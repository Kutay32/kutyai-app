"""API anahtarı uçları (API §7).

Tam anahtar yalnızca oluşturma yanıtında bir kez döner; sonraki okumalar
`onek`/`son_dort` ile temsil edilir.
"""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.guvenlik import api_anahtari_uret
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizIstek
from bdm_veritabani.modeller import AnahtarDurumu, ApiAnahtari, Bdm, Kullanici

router = APIRouter()


class AnahtarOlustur(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ad: str = Field(min_length=2, max_length=160)
    izinli_modeller: list[str] = Field(default_factory=list)
    gunluk_istek_siniri: int | None = Field(default=None, ge=1, le=10_000_000)
    kullanici_id: int | None = None


def _sozluk(anahtar: ApiAnahtari) -> dict[str, object]:
    """Anahtarı gizli parçası olmadan temsil eder."""
    return {
        "id": anahtar.id,
        "ad": anahtar.ad,
        "onek": anahtar.onek,
        "son_dort": anahtar.son_dort,
        "durum": anahtar.durum.value,
        "izinli_modeller": list(anahtar.izinli_modeller or []),
        "gunluk_istek_siniri": anahtar.gunluk_istek_siniri,
        "olusturulma": anahtar.olusturulma.isoformat() if anahtar.olusturulma else None,
        "son_kullanim": anahtar.son_kullanim.isoformat() if anahtar.son_kullanim else None,
    }


async def _izinli_modelleri_dogrula(
    oturum: AsyncSession, modeller: list[str]
) -> list[str]:
    """Model slug'ı ya da kimliği olmayan girdileri reddeder; boş liste tümü demektir."""
    temiz = [str(parca).strip() for parca in modeller if str(parca).strip()]
    if not temiz:
        return []
    bilinen = {
        str(deger)
        for satir in (await oturum.execute(sa.select(Bdm.id, Bdm.slug))).all()
        for deger in satir
    }
    bilinmeyen = sorted({parca for parca in temiz if parca not in bilinen})
    if bilinmeyen:
        raise GecersizIstek(
            "Bilinmeyen model seçildi.", {"gecersiz": bilinmeyen}
        )
    return temiz


@router.get("/api-anahtarlari")
async def anahtarlari_listele(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _personel: Kullanici = Depends(gecerli_personel()),
) -> list[dict[str, object]]:
    """Personel için tüm API anahtarlarını maskeli olarak listeler."""
    satirlar = (
        await oturum.execute(
            sa.select(ApiAnahtari).order_by(
                ApiAnahtari.olusturulma.desc(), ApiAnahtari.id.desc()
            )
        )
    ).scalars().all()
    return [_sozluk(anahtar) for anahtar in satirlar]


@router.post("/api-anahtarlari", status_code=201)
async def anahtar_olustur(
    govde: AnahtarOlustur,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Yeni API anahtarı üretir; tam anahtar yalnız bu yanıtta döner."""
    izinli = await _izinli_modelleri_dogrula(oturum, govde.izinli_modeller)
    if govde.kullanici_id is not None:
        sahibi = await oturum.get(Kullanici, govde.kullanici_id)
        if sahibi is None:
            raise GecersizIstek(
                "Belirtilen kullanıcı bulunamadı.", {"alan": "kullanici_id"}
            )

    uretilen = api_anahtari_uret()
    anahtar = ApiAnahtari(
        ad=govde.ad,
        onek=uretilen["onek"],
        anahtar_hash=uretilen["hash"],
        son_dort=uretilen["son_dort"],
        kullanici_id=govde.kullanici_id,
        izinli_modeller=izinli,
        gunluk_istek_siniri=govde.gunluk_istek_siniri,
    )
    oturum.add(anahtar)
    await oturum.flush()
    await oturum.refresh(anahtar)

    await islem_kaydet(
        oturum,
        "api_anahtari.olusturuldu",
        kullanici_id=personel.id,
        hedef_tur="api_anahtari",
        hedef_id=anahtar.id,
        ayrinti={"ad": anahtar.ad, "izinli_modeller": izinli},
    )
    return {**_sozluk(anahtar), "tam_anahtar": uretilen["tam"]}


@router.post("/api-anahtarlari/{anahtar_id}/iptal")
async def anahtar_iptal(
    anahtar_id: int,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    personel: Kullanici = Depends(gecerli_personel()),
) -> dict[str, object]:
    """Anahtarı iptal eder; iptal edilmiş anahtar kimlik doğrulamada reddedilir."""
    anahtar = await oturum.get(ApiAnahtari, anahtar_id)
    if anahtar is None:
        raise Bulunamadi("API anahtarı bulunamadı.", {"api_anahtari_id": anahtar_id})

    anahtar.durum = AnahtarDurumu.iptal
    await oturum.flush()
    await islem_kaydet(
        oturum,
        "api_anahtari.iptal_edildi",
        kullanici_id=personel.id,
        hedef_tur="api_anahtari",
        hedef_id=anahtar.id,
        ayrinti={"ad": anahtar.ad},
    )
    return {"durum": anahtar.durum.value}
