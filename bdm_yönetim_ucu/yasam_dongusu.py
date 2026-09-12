"""BDM yaşam döngüsü: durum makinesi ve konteyner işlemleri (spec §7.6, §10)."""

from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.hatalar import (
    BdmHazirDegil,
    GecersizGecis,
    SurucuYok,
    UstSaglayiciHatasi,
)
from arkauc.app.servisler.konteyner import KonteynerSurucusu, SaglikDurumu, surucu_al
from bdm_listesi import bdm_sozlugu
from bdm_listesi.saglayicilar import saglayici_bilgisi
from bdm_veritabani.modeller import Bdm, BdmDurumu

logger = logging.getLogger("kutyai.yonetim")

# spec §10: GPU'suz ortamda GPU gerektiren saglayici icin kullaniciya gosterilen metin.
GPU_GEREKLI_MESAJ = (
    "Bu model GPU gerektirir; Ollama gibi CPU uyumlu bir sağlayıcı seçin "
    "veya GPU çalışma zamanını kurun."
)

# Durum makinesi: taslak → hazir → calisiyor → durdu; `hata` her durumdan girilebilir.
# `hata`dan çıkış yöneticinin kurtarma yollarıdır: `durdu` (durdur ucu) ve
# `hazir` (doğrulama ucu); `calisiyor`a doğrudan geçiş yoktur.
gecerli_gecisler: dict[BdmDurumu, frozenset[BdmDurumu]] = {
    BdmDurumu.taslak: frozenset({BdmDurumu.hazir, BdmDurumu.hata}),
    BdmDurumu.hazir: frozenset({BdmDurumu.calisiyor, BdmDurumu.taslak, BdmDurumu.hata}),
    BdmDurumu.calisiyor: frozenset({BdmDurumu.durdu, BdmDurumu.hata}),
    BdmDurumu.durdu: frozenset({BdmDurumu.calisiyor, BdmDurumu.hazir, BdmDurumu.hata}),
    BdmDurumu.hata: frozenset({BdmDurumu.taslak, BdmDurumu.hazir, BdmDurumu.durdu, BdmDurumu.hata}),
}


def gecis_dogrula(bdm: Bdm, hedef: BdmDurumu) -> None:
    """Geçiş durum makinesine uygun değilse `409 gecersiz_gecis` fırlatır."""
    if hedef not in gecerli_gecisler.get(bdm.durum, frozenset()):
        raise GecersizGecis(
            f"'{bdm.durum.value}' durumundan '{hedef.value}' durumuna geçilemez.",
            {"mevcut": bdm.durum.value, "hedef": hedef.value},
        )


def izinli_kaynaklar(hedef: BdmDurumu) -> tuple[BdmDurumu, ...]:
    """Durum makinesine göre `hedef`e geçişe izin veren kaynak durumlar."""
    return tuple(durum for durum, hedefler in gecerli_gecisler.items() if hedef in hedefler)


async def gecisi_kilitle(
    oturum: AsyncSession,
    bdm: Bdm,
    hedef: BdmDurumu,
    *,
    kaynaklar: tuple[BdmDurumu, ...] | None = None,
) -> None:
    """Durum geçişini koşullu tek UPDATE ile atomik olarak kilitler.

    `UPDATE bdm SET durum=<hedef> WHERE id=? AND durum IN (<kaynaklar>)`; eşzamanlı
    isteklerden yalnızca biri `rowcount=1` görür, diğerleri `409 gecersiz_gecis`
    alır. Böylece oku-denetle-yaz yarışı kapanır ve konteyner gibi kaynakları
    yalnızca geçişi kazanan istek başlatır.

    Hedef durum kaynak kümesinden çıkarılır; aksi hâlde kilitlenen satır ikinci bir
    istekçe yeniden eşleştirilebilirdi. `kaynaklar` verilmezse durum makinesinden
    türetilir ve hedef ayıklanır.
    """
    kaynak_kumesi = kaynaklar if kaynaklar is not None else izinli_kaynaklar(hedef)
    izinli = tuple(durum for durum in kaynak_kumesi if durum is not hedef)
    if not izinli:
        # Çağıran hatası: hedefe giden kaynak kümesi yanlış kurgulanmış.
        raise GecersizGecis(
            f"'{hedef.value}' durumuna geçiş tanımlı değil.",
            {"hedef": hedef.value},
        )
    sonuc = await oturum.execute(
        sa.update(Bdm).where(Bdm.id == bdm.id, Bdm.durum.in_(izinli)).values(durum=hedef)
    )
    if int(sonuc.rowcount or 0) != 1:
        await oturum.refresh(bdm)
        gecis_dogrula(bdm, hedef)
        raise GecersizGecis(
            f"'{bdm.durum.value}' durumundan '{hedef.value}' durumuna geçilemez.",
            {"mevcut": bdm.durum.value, "hedef": hedef.value},
        )
    bdm.durum = hedef


def _hata_kodu(hata: BaseException) -> str:
    """Denetim izi için hata kodunu sadeleştirir."""
    kod = getattr(hata, "kod", None)
    return str(kod) if kod else type(hata).__name__


async def manifest_al(bdm: Bdm) -> dict[str, Any]:
    """Konteyner manifestini hazırlama modülünden ister (spec §7.5)."""
    try:
        from bdm_hazırlama_ucu.manifest import manifest_uret
    except ImportError as hata:
        raise BdmHazirDegil("Hazırlama modülü henüz kullanılamıyor.") from hata
    manifest = manifest_uret(bdm)
    if not isinstance(manifest, dict):
        raise BdmHazirDegil("Hazırlama modülü geçerli bir konteyner manifesti üretmedi.")
    return manifest


def surucu_sec(bdm: Bdm) -> KonteynerSurucusu:
    """Sağlayıcı ve yerellik bilgisine göre sürücüyü seçer."""
    return surucu_al(bdm.saglayici.value, bdm.yerel_mi)


def konteyner_kimligi(bdm: Bdm, *, zorunlu: bool = True) -> str | None:
    """BDM kaydındaki konteyner kimliğini döndürür."""
    ham = (bdm.konteyner or {}).get("konteyner_id")
    if not ham:
        if zorunlu:
            raise SurucuYok("Bu model için çalışan konteyner kaydı yok.", {"bdm_id": bdm.id})
        return None
    return str(ham)


def _konteyner_kaydi(bdm: Bdm, manifest: dict[str, Any], konteyner_id: str) -> dict[str, Any]:
    """Konteyner JSON'unu günceller; rota tercihleri (`yol`) korunur."""
    return {
        **(bdm.konteyner or {}),
        "image": manifest.get("image"),
        "gpu": bool(manifest.get("gpu")),
        "port": manifest.get("port"),
        "bellek_gb": manifest.get("bellek_gb"),
        "konteyner_id": konteyner_id,
    }


async def _eski_konteyneri_kaldir(bdm: Bdm, surucu: KonteynerSurucusu) -> None:
    """Varsa önceki konteyneri durdurup siler (en iyi çaba).

    Yerel sürücüde durdurma modeli boşaltmak için Ollama'ya istek atar; sunucu
    yanıt vermezse `UstSaglayiciHatasi` yükselir. Bu, yeni başlatmayı engellemez:
    `baslat` zaten sunucu erişilebilirliğini kendi yoklamasıyla denetler.
    """
    kimlik = konteyner_kimligi(bdm, zorunlu=False)
    if kimlik is None:
        return
    for islem in (surucu.durdur, surucu.sil):
        try:
            await islem(kimlik)
        except (SurucuYok, UstSaglayiciHatasi) as hata:
            logger.warning(
                "Eski konteyner kaldırılamadı (%s/%s): %s", islem.__name__, kimlik, hata.mesaj
            )


async def _calistir(bdm: Bdm, surucu: KonteynerSurucusu) -> str:
    """GPU denetimi, manifest ve konteyner başlatma; geçiş uygulamaz."""
    durum = await surucu.durum()
    if saglayici_bilgisi(bdm.saglayici.value).gpu_gerekir and not durum.gpu_var:
        raise SurucuYok(GPU_GEREKLI_MESAJ, {"saglayici": bdm.saglayici.value})
    manifest = await manifest_al(bdm)
    konteyner_id = await surucu.baslat(bdm_sozlugu(bdm), manifest)
    bdm.konteyner = _konteyner_kaydi(bdm, manifest, konteyner_id)
    return konteyner_id


async def _kaydet(
    oturum: AsyncSession,
    eylem: str,
    bdm: Bdm,
    surucu: KonteynerSurucusu,
    konteyner_id: str | None,
    *,
    kullanici_id: int | None,
    ip: str,
) -> None:
    await islem_kaydet(
        oturum,
        eylem,
        kullanici_id=kullanici_id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"konteyner_id": konteyner_id or "", "surucu": surucu.ad},
        ip=ip,
    )


async def _basarisiz_baslatma(
    oturum: AsyncSession,
    bdm: Bdm,
    surucu: KonteynerSurucusu,
    hata: BaseException,
    *,
    eylem: str,
    kullanici_id: int | None,
    ip: str,
) -> None:
    """Başarısız başlatmayı `hata`ya çeker: konteyner kaydı temizlenir, iz bırakılır.

    `yol` (rota tercihleri) korunur; yalnızca konteynere ait alanlar silinir.
    """
    kalan = {
        anahtar: deger for anahtar, deger in (bdm.konteyner or {}).items() if anahtar == "yol"
    }
    bdm.konteyner = kalan or None
    await gecisi_kilitle(oturum, bdm, BdmDurumu.hata, kaynaklar=(BdmDurumu.calisiyor,))
    await islem_kaydet(
        oturum,
        eylem,
        kullanici_id=kullanici_id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"surucu": surucu.ad, "hata": _hata_kodu(hata)},
        ip=ip,
    )
    await oturum.commit()


async def _durdurmayi_geri_al(
    oturum: AsyncSession,
    bdm: Bdm,
    onceki: BdmDurumu,
    surucu: KonteynerSurucusu,
    hata: BaseException,
    *,
    kullanici_id: int | None,
    ip: str,
) -> None:
    """Başarısız durdurmada kilidi geri alır (konteyner hâlâ çalışıyor olabilir)."""
    await gecisi_kilitle(oturum, bdm, onceki, kaynaklar=(BdmDurumu.durdu,))
    await islem_kaydet(
        oturum,
        "bdm.durdurulamadi",
        kullanici_id=kullanici_id,
        hedef_tur="bdm",
        hedef_id=bdm.id,
        ayrinti={"surucu": surucu.ad, "hata": _hata_kodu(hata)},
        ip=ip,
    )
    await oturum.commit()


async def _konteyneri_baslat(
    oturum: AsyncSession,
    bdm: Bdm,
    *,
    kaynaklar: tuple[BdmDurumu, ...],
    basari_eylemi: str,
    hata_eylemi: str,
    kullanici_id: int | None,
    ip: str,
) -> dict[str, Any]:
    """Geçişi kilitler ve konteyneri YALNIZCA kilidi kazanan istek için başlatır."""
    await gecisi_kilitle(oturum, bdm, BdmDurumu.calisiyor, kaynaklar=kaynaklar)
    # Kilidi hemen bırak: konteyner başlatma yavaş olabilir, eşzamanlı istekler
    # yazma kilidinde beklemeden `409` alsın.
    await oturum.commit()
    surucu = surucu_sec(bdm)
    try:
        await _eski_konteyneri_kaldir(bdm, surucu)
        konteyner_id = await _calistir(bdm, surucu)
    except Exception as hata:
        await _basarisiz_baslatma(
            oturum, bdm, surucu, hata, eylem=hata_eylemi, kullanici_id=kullanici_id, ip=ip
        )
        raise
    await _kaydet(
        oturum, basari_eylemi, bdm, surucu, konteyner_id, kullanici_id=kullanici_id, ip=ip
    )
    await oturum.commit()
    return {"durum": bdm.durum.value, "konteyner_id": konteyner_id}


async def baslat(
    oturum: AsyncSession,
    bdm: Bdm,
    *,
    kullanici_id: int | None = None,
    ip: str = "",
) -> dict[str, Any]:
    """BDM'yi `hazir`/`durdu` durumundan `calisiyor` durumuna geçirir."""
    return await _konteyneri_baslat(
        oturum,
        bdm,
        kaynaklar=izinli_kaynaklar(BdmDurumu.calisiyor),
        basari_eylemi="bdm.baslatildi",
        hata_eylemi="bdm.baslatilamadi",
        kullanici_id=kullanici_id,
        ip=ip,
    )


async def durdur(
    oturum: AsyncSession,
    bdm: Bdm,
    *,
    kullanici_id: int | None = None,
    ip: str = "",
) -> dict[str, Any]:
    """Çalışan konteyneri durdurur (`calisiyor`/`hata` → `durdu`).

    Geçiş koşullu UPDATE ile kilitlenir; sürücüyü yalnızca kilidi kazanan istek
    çağırır. `hata` durumundan çıkış bir kurtarma yoludur: kayıtlı konteyner yoksa
    ya da çalışma zamanı onu tanımıyorsa/durduramıyorsa kesinti loga yazılır ve
    geçiş yine uygulanır (yönetici kilitlenmez). `calisiyor`dan çıkışta hata
    yutulmaz: kilit geri alınır ve hata çağırana bırakılır.
    """
    onceki = bdm.durum
    kurtarma = onceki is BdmDurumu.hata
    kimlik = konteyner_kimligi(bdm, zorunlu=not kurtarma)
    await gecisi_kilitle(oturum, bdm, BdmDurumu.durdu)
    await oturum.commit()
    surucu = surucu_sec(bdm)
    if kimlik is not None:
        try:
            await surucu.durdur(kimlik)
        except (SurucuYok, UstSaglayiciHatasi) as hata:
            if not kurtarma:
                await _durdurmayi_geri_al(
                    oturum, bdm, onceki, surucu, hata, kullanici_id=kullanici_id, ip=ip
                )
                raise
            logger.warning(
                "BDM %s hata durumundan çıkarılırken konteyner durdurulamadı (%s): %s",
                bdm.id,
                kimlik,
                hata.mesaj,
            )
    await _kaydet(
        oturum, "bdm.durduruldu", bdm, surucu, kimlik, kullanici_id=kullanici_id, ip=ip
    )
    await oturum.commit()
    return {"durum": bdm.durum.value}


async def yeniden_baslat(
    oturum: AsyncSession,
    bdm: Bdm,
    *,
    kullanici_id: int | None = None,
    ip: str = "",
) -> dict[str, Any]:
    """Çalışan konteyneri durdurup aynı BDM için yenisini başlatır."""
    if bdm.durum is BdmDurumu.calisiyor:
        # Önce durdurma kilidi: eşzamanlı yeniden başlatmalardan yalnızca biri geçer.
        await gecisi_kilitle(oturum, bdm, BdmDurumu.durdu, kaynaklar=(BdmDurumu.calisiyor,))
        await oturum.commit()
    elif bdm.durum is not BdmDurumu.durdu:
        raise GecersizGecis(
            f"'{bdm.durum.value}' durumundan '{BdmDurumu.calisiyor.value}' durumuna geçilemez.",
            {"mevcut": bdm.durum.value, "hedef": BdmDurumu.calisiyor.value},
        )
    return await _konteyneri_baslat(
        oturum,
        bdm,
        kaynaklar=(BdmDurumu.durdu,),
        basari_eylemi="bdm.yeniden_baslatildi",
        hata_eylemi="bdm.yeniden_baslatilamadi",
        kullanici_id=kullanici_id,
        ip=ip,
    )


async def saglik_al(bdm: Bdm) -> SaglikDurumu:
    """Çalışan konteynerin sağlığını döndürür; kayıt yoksa sağlıksız kabul eder."""
    kimlik = konteyner_kimligi(bdm, zorunlu=False)
    if kimlik is None:
        return SaglikDurumu(
            calisiyor=False, hazir=False, mesaj="Bu model için çalışan konteyner kaydı yok."
        )
    try:
        return await surucu_sec(bdm).saglik(kimlik)
    except SurucuYok as hata:
        return SaglikDurumu(calisiyor=False, hazir=False, mesaj=hata.mesaj)
