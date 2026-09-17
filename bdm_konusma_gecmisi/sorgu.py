"""Konusma ve kullanim sorgulari (spec §7.7, §12, §13)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bdm_veritabani.modeller import (
    Bdm,
    KullanimKaydi,
    KullanimDurumu,
    Konusma,
    Kullanici,
    Mesaj,
)

VARSAYILAN_SAYFA_BOYUTU = 25
EN_BUYUK_SAYFA_BOYUTU = 200


def _sinirla(sayfa: int, boyut: int) -> tuple[int, int]:
    sayfa = max(1, int(sayfa or 1))
    boyut = min(max(1, int(boyut or VARSAYILAN_SAYFA_BOYUTU)), EN_BUYUK_SAYFA_BOYUTU)
    return sayfa, boyut


async def konusmalari_listele(
    oturum: AsyncSession,
    *,
    org_id: int | None = None,
    kullanici_id: int | None = None,
    api_anahtari_id: int | None = None,
    bdm_id: int | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    arama: str | None = None,
    sayfa: int = 1,
    boyut: int = VARSAYILAN_SAYFA_BOYUTU,
) -> dict[str, object]:
    sayfa, boyut = _sinirla(sayfa, boyut)

    kosullar: list[sa.ColumnElement[bool]] = []
    if org_id is not None:
        kosullar.append(Konusma.org_id == org_id)
    if kullanici_id is not None:
        kosullar.append(Konusma.kullanici_id == kullanici_id)
    if api_anahtari_id is not None:
        kosullar.append(Konusma.api_anahtari_id == api_anahtari_id)
    if bdm_id is not None:
        kosullar.append(Konusma.bdm_id == bdm_id)
    if baslangic is not None:
        kosullar.append(Konusma.olusturulma >= baslangic)
    if bitis is not None:
        kosullar.append(Konusma.olusturulma <= bitis)
    if arama:
        desen = f"%{arama.strip()}%"
        kosullar.append(
            sa.or_(
                Konusma.baslik.ilike(desen),
                sa.exists().where(
                    sa.and_(Mesaj.konusma_id == Konusma.id, Mesaj.icerik.ilike(desen))
                ),
            )
        )

    toplam = (
        await oturum.execute(
            sa.select(sa.func.count()).select_from(Konusma).where(*kosullar)
        )
    ).scalar_one()

    satirlar = (
        await oturum.execute(
            sa.select(Konusma, Kullanici.eposta, Bdm.gorunen_ad)
            .outerjoin(Kullanici, Kullanici.id == Konusma.kullanici_id)
            .outerjoin(Bdm, Bdm.id == Konusma.bdm_id)
            .where(*kosullar)
            .order_by(Konusma.guncellenme.desc(), Konusma.id.desc())
            .offset((sayfa - 1) * boyut)
            .limit(boyut)
        )
    ).all()

    kimlikler = [satir[0].id for satir in satirlar]
    sayilar: dict[int, int] = {}
    if kimlikler:
        sayilar = dict(
            (
                await oturum.execute(
                    sa.select(Mesaj.konusma_id, sa.func.count())
                    .where(Mesaj.konusma_id.in_(kimlikler))
                    .group_by(Mesaj.konusma_id)
                )
            ).all()
        )

    kayitlar = [
        {
            "id": konusma.id,
            "baslik": konusma.baslik,
            "kullanici_id": konusma.kullanici_id,
            "kullanici_eposta": eposta,
            "api_anahtari_id": konusma.api_anahtari_id,
            "bdm_id": konusma.bdm_id,
            "bdm_ad": bdm_ad,
            "mesaj_sayisi": int(sayilar.get(konusma.id, 0)),
            "token_girdi": konusma.token_girdi or 0,
            "token_cikti": konusma.token_cikti or 0,
            "olusturulma": konusma.olusturulma.isoformat(),
            "guncellenme": konusma.guncellenme.isoformat(),
        }
        for konusma, eposta, bdm_ad in satirlar
    ]
    return {"toplam": int(toplam), "sayfa": sayfa, "boyut": boyut, "kayitlar": kayitlar}


async def konusma_detayi(oturum: AsyncSession, konusma: Konusma) -> dict[str, object]:
    bdm_ad = (
        await oturum.execute(sa.select(Bdm.gorunen_ad).where(Bdm.id == konusma.bdm_id))
    ).scalar_one_or_none()
    kullanici_eposta = None
    if konusma.kullanici_id is not None:
        kullanici_eposta = (
            await oturum.execute(
                sa.select(Kullanici.eposta).where(Kullanici.id == konusma.kullanici_id)
            )
        ).scalar_one_or_none()
    mesajlar = (
        await oturum.execute(
            sa.select(Mesaj).where(Mesaj.konusma_id == konusma.id).order_by(Mesaj.id)
        )
    ).scalars().all()
    return {
        "id": konusma.id,
        "baslik": konusma.baslik,
        "bdm_id": konusma.bdm_id,
        "bdm_ad": bdm_ad,
        "kullanici_id": konusma.kullanici_id,
        "kullanici_eposta": kullanici_eposta,
        "api_anahtari_id": konusma.api_anahtari_id,
        "sistem_istemi": konusma.sistem_istemi,
        "token_girdi": konusma.token_girdi or 0,
        "token_cikti": konusma.token_cikti or 0,
        "olusturulma": konusma.olusturulma.isoformat(),
        "guncellenme": konusma.guncellenme.isoformat(),
        "mesajlar": [
            {
                "id": mesaj.id,
                "rol": mesaj.rol.value,
                "icerik": mesaj.icerik,
                "token_sayisi": mesaj.token_sayisi or 0,
                "gecikme_ms": mesaj.gecikme_ms or 0,
                "model": mesaj.model,
                "hata": mesaj.hata,
                "olusturulma": mesaj.olusturulma.isoformat(),
            }
            for mesaj in mesajlar
        ],
    }


async def konusma_sahibi_mi(
    oturum: AsyncSession,
    konusma: Konusma,
    *,
    kullanici_id: int | None,
    api_anahtari_id: int | None,
) -> bool:
    if kullanici_id is not None and konusma.kullanici_id == kullanici_id:
        return True
    if api_anahtari_id is not None and konusma.api_anahtari_id == api_anahtari_id:
        return True
    return False


async def kullanim_ozeti(
    oturum: AsyncSession, *, gun: int = 30, org_id: int | None = None
) -> dict[str, object]:
    esik = datetime.now(timezone.utc) - timedelta(days=max(1, int(gun)))
    kosullar: list[sa.ColumnElement[bool]] = [KullanimKaydi.olusturulma >= esik]
    if org_id is not None:
        kosullar.append(KullanimKaydi.org_id == org_id)
    satirlar = (
        await oturum.execute(
            sa.select(
                KullanimKaydi.durum,
                sa.func.count(),
                sa.func.coalesce(sa.func.sum(KullanimKaydi.girdi_token), 0),
                sa.func.coalesce(sa.func.sum(KullanimKaydi.cikti_token), 0),
            )
            .where(*kosullar)
            .group_by(KullanimKaydi.durum)
        )
    ).all()

    gecikme_kosullari = [*kosullar, KullanimKaydi.gecikme_ms > 0]
    gecikme_toplam, gecikme_adet = (
        await oturum.execute(
            sa.select(
                sa.func.coalesce(sa.func.sum(KullanimKaydi.gecikme_ms), 0),
                sa.func.coalesce(
                    sa.func.sum(sa.case((KullanimKaydi.gecikme_ms > 0, 1), else_=0)), 0
                ),
            ).where(*gecikme_kosullari)
        )
    ).one()

    ozet: dict[str, object] = {
        "toplam_istek": 0,
        "toplam_token": 0,
        "basarili": 0,
        "hatali": 0,
        "kota_asimi": 0,
        "ortalama_gecikme_ms": 0,
    }
    for durum, adet, girdi, cikti in satirlar:
        adet = int(adet)
        ozet["toplam_istek"] = int(ozet["toplam_istek"]) + adet
        ozet["toplam_token"] = int(ozet["toplam_token"]) + int(girdi) + int(cikti)
        if durum == KullanimDurumu.basarili:
            ozet["basarili"] = int(ozet["basarili"]) + adet
        elif durum == KullanimDurumu.kota_asildi:
            ozet["kota_asimi"] = int(ozet["kota_asimi"]) + adet
        else:
            ozet["hatali"] = int(ozet["hatali"]) + adet
    if int(gecikme_adet):
        ozet["ortalama_gecikme_ms"] = round(int(gecikme_toplam) / int(gecikme_adet))
    ozet["gun"] = max(1, int(gun))
    return ozet


async def kullanim_zaman_serisi(
    oturum: AsyncSession,
    *,
    gun: int = 30,
    kirilim: str = "bdm",
    org_id: int | None = None,
) -> dict[str, object]:
    """Gunluk istek/token serisi; toplama Python tarafinda yapilir (tasınabilirlik)."""
    gun = max(1, min(int(gun), 365))
    esik = datetime.now(timezone.utc) - timedelta(days=gun)
    etiket_sutunu = Bdm.gorunen_ad if kirilim == "bdm" else Kullanici.eposta

    sorgu = sa.select(
        KullanimKaydi.olusturulma,
        KullanimKaydi.girdi_token,
        KullanimKaydi.cikti_token,
        etiket_sutunu,
    ).where(KullanimKaydi.olusturulma >= esik)
    if org_id is not None:
        sorgu = sorgu.where(KullanimKaydi.org_id == org_id)
    if kirilim == "bdm":
        sorgu = sorgu.outerjoin(Bdm, Bdm.id == KullanimKaydi.bdm_id)
    else:
        sorgu = sorgu.outerjoin(Kullanici, Kullanici.id == KullanimKaydi.kullanici_id)

    satirlar = (await oturum.execute(sorgu)).all()
    gunluk: dict[str, dict[str, int]] = {}
    toplam: dict[str, dict[str, int]] = {}
    for olusturulma, girdi, cikti, etiket in satirlar:
        anahtar = olusturulma.date().isoformat()
        token = int(girdi or 0) + int(cikti or 0)
        kayit = gunluk.setdefault(anahtar, {})
        kayit[etiket or "bilinmeyen"] = kayit.get(etiket or "bilinmeyen", 0) + token
        ad = etiket or "bilinmeyen"
        toplam.setdefault(ad, {"istek": 0, "token": 0})
        toplam[ad]["istek"] += 1
        toplam[ad]["token"] += token

    return {
        "gun": gun,
        "kirilim": kirilim,
        "seri": [
            {"etiket": etiket, "istek": deger["istek"], "token": deger["token"]}
            for etiket, deger in sorted(toplam.items(), key=lambda x: -x[1]["token"])
        ],
        "gunluk": [
            {"tarih": tarih, "token": sum(deger.values())}
            for tarih, deger in sorted(gunluk.items())
        ],
    }
