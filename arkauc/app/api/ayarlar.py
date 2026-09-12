"""Ayar uçları (API §14).

Okuma/yazma yalnızca yöneticiye açıktır. `smtp_sifre` veritabanına Fernet ile
şifrelenerek yazılır ve hiçbir yanıtta döndürülmez; yalnızca `smtp_tanimli`
bayrağı raporlanır. Şifreli değeri yalnızca posta sürücüsü çözer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.ayarlar_db import ayar_oku, ayar_yaz
from arkauc.app.cekirdek.bagimliliklar import gecerli_personel, veritabani_oturumu
from arkauc.app.cekirdek.denetim import islem_kaydet
from arkauc.app.cekirdek.guvenlik import sifrele
from bdm_veritabani.modeller import Kullanici, Rol

router = APIRouter()


class AyarGuncelle(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    marka_adi: str | None = Field(default=None, min_length=1, max_length=160)
    saklama_gun: int | None = Field(default=None, ge=1, le=3650)
    maskeleme_aktif: bool | None = None
    kayit_acik: bool | None = None
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_kullanici: str | None = Field(default=None, max_length=255)
    smtp_sifre: str | None = Field(default=None, max_length=400)
    smtp_gonderen: str | None = Field(default=None, max_length=255)
    smtp_tls: bool | None = None
    bakim_modu: bool | None = None


async def _deger(oturum: AsyncSession, anahtar: str, ortam: Any) -> Any:
    """Veritabanı değeri varsa onu, yoksa ortam varsayılanını döndürür."""
    deger = await ayar_oku(oturum, anahtar, None)
    return ortam if deger is None else deger


async def _etkin_ayarlar(oturum: AsyncSession) -> dict[str, object]:
    smtp_host = str(await _deger(oturum, "smtp_host", ayarlar.smtp_host) or "")
    return {
        "marka_adi": str(await _deger(oturum, "marka_adi", "KutyAI")),
        "kurulum_tamam": bool(await ayar_oku(oturum, "kurulum_tamam", False)),
        "saklama_gun": int(await _deger(oturum, "saklama_gun", ayarlar.saklama_gun)),
        "maskeleme_aktif": bool(
            await _deger(oturum, "maskeleme_aktif", ayarlar.maskeleme_aktif)
        ),
        "kayit_acik": bool(await _deger(oturum, "kayit_acik", True)),
        "smtp_host": smtp_host,
        "smtp_gonderen": str(
            await _deger(oturum, "smtp_gonderen", ayarlar.smtp_gonderen) or ""
        ),
        "smtp_tanimli": bool(smtp_host.strip()),
        "bakim_modu": bool(await _deger(oturum, "bakim_modu", False)),
    }


@router.get("/ayarlar")
async def ayarlari_getir(
    oturum: AsyncSession = Depends(veritabani_oturumu),
    _yonetici: Kullanici = Depends(gecerli_personel((Rol.yonetici,))),
) -> dict[str, object]:
    """Etkin ayarları döndürür; SMTP parolası asla yer almaz."""
    return await _etkin_ayarlar(oturum)


@router.put("/ayarlar")
async def ayarlari_guncelle(
    govde: AyarGuncelle,
    oturum: AsyncSession = Depends(veritabani_oturumu),
    yonetici: Kullanici = Depends(gecerli_personel((Rol.yonetici,))),
) -> dict[str, object]:
    """Yalnızca gönderilen alanları günceller ve denetim izine yazar."""
    degisenler = {
        anahtar: deger
        for anahtar, deger in govde.model_dump(exclude_unset=True).items()
        if deger is not None
    }
    anahtarlar = sorted(degisenler)
    for anahtar, deger in degisenler.items():
        # SMTP parolası düz metin saklanmaz; boş değer ayarı temizler.
        if anahtar == "smtp_sifre":
            deger = sifrele(deger) if deger else ""
        await ayar_yaz(oturum, anahtar, deger)

    if anahtarlar:
        await islem_kaydet(
            oturum,
            "ayar.guncellendi",
            kullanici_id=yonetici.id,
            hedef_tur="ayar",
            ayrinti={"anahtarlar": anahtarlar},
        )
    return await _etkin_ayarlar(oturum)
