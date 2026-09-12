"""Dosya saklama, metin cikarimi ve sohbet baglami (spec §3).

Dosyalar `<dizin>/<org_slug>/<uuid4>` altinda tutulur; `dosya.yol` mutlak yolu
saklar. Metin cikarimi `text/*`, `application/json` ve `application/pdf` icin
yapilir; diger turlerde `metin` bos kalir — **uydurma metin yok**. Cikarilan
metin KVKK kurallarindan gecirilerek `dosya.metin` kolonuna yazilir; bu yuzden
`baglam_metni` cagiran taraf da maskeli metin gorur.

`dosya_kaydet` MIME/boyut dogrulamasi yapmaz; bunlar uç katmaninin isidir
(medya uretimi gibi ic kaynaklar sinirli turleri de saklayabilmelidir).
"""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from functools import lru_cache
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import Bulunamadi, GecersizIstek
from bdm_konusma_gecmisi.maskeleme import maskele_metin
from bdm_veritabani.modeller import Dosya, Organizasyon

logger = logging.getLogger("kutyai.dosya")

#: Dogrudan metne cevrilen tam MIME turleri.
METIN_TAM_MIME: frozenset[str] = frozenset({"application/json"})
#: Metne cevrilen MIME onekleri (`text/*` ve dolayisiyla `text/csv`).
METIN_MIME_ONEKLERI: tuple[str, ...] = ("text/",)

#: Izinli MIME: tam eslesme.
IZINLI_TAM_MIME: frozenset[str] = frozenset({"application/json", "application/pdf"})
#: Izinli MIME: onek eslesmesi (`text/*`, `image/*`).
IZINLI_MIME_ONEKLERI: tuple[str, ...] = ("text/", "image/")

#: `application/octet-stream` (ya da bos tur) icin uzantidan cikarilan turler.
UZANTI_MIME: dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".log": "text/plain",
    ".json": "application/json",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
}

#: Metin cikarilamayan dosyalar icin katalog gerekcesi.
METIN_GEREKCESI = "dosya_metni_cikarilamadi"


def _temel_mime(mime: str | None) -> str:
    """Parametreleri atilmis, kucuk harfli MIME turu."""
    return (mime or "").split(";")[0].strip().lower()


def mime_coz(ham: str | None, ad: str) -> str:
    """Yuklenen dosyanin MIME turunu cozer.

    `application/octet-stream` (ya da bos) ise uzantidan cikarilir; sonuc
    izinli listede degilse `400 dosya_tur_desteklenmiyor`.
    """
    mime = _temel_mime(ham)
    if mime in ("", "application/octet-stream"):
        mime = UZANTI_MIME.get(Path(ad).suffix.lower(), "")
    if mime and (mime in IZINLI_TAM_MIME or mime.startswith(IZINLI_MIME_ONEKLERI)):
        return mime
    raise GecersizIstek(
        "dosya_tur_desteklenmiyor",
        {"mime": ham or None, "ad": ad},
        kod="dosya_tur_desteklenmiyor",
    )


def metin_destekli_mi(mime: str | None) -> bool:
    """Bu turden metin cikarilabilir mi?"""
    temel = _temel_mime(mime)
    return temel in METIN_TAM_MIME or temel.startswith(METIN_MIME_ONEKLERI)


@lru_cache(maxsize=1)
def _pdf_okuyucu() -> type | None:
    """`pypdf` kuruluysa okuyucu sinifi, degilse None (tek seferlik deneme)."""
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        return None
    return PdfReader


def _pdf_metni(icerik: bytes) -> tuple[str, str | None]:
    okuyucu = _pdf_okuyucu()
    if okuyucu is None:
        return "", METIN_GEREKCESI
    try:
        belge = okuyucu(io.BytesIO(icerik))
        sayfalar = [(sayfa.extract_text() or "") for sayfa in belge.pages]
    except Exception:  # bozuk/taranmis PDF: uydurma yok, gerekce dondurulur
        logger.info("PDF metni cikarilamadi; dosya bozuk ya da taranmis olabilir.")
        return "", METIN_GEREKCESI
    return "\n".join(sayfalar).strip(), None


def icerik_metni(icerik: bytes, mime: str | None) -> tuple[str, str | None]:
    """Bellekteki icerikten metin cikarir: `(metin, gerekce)`."""
    temel = _temel_mime(mime)
    if metin_destekli_mi(temel):
        return icerik.decode("utf-8", errors="replace"), None
    if temel == "application/pdf":
        return _pdf_metni(icerik)
    return "", METIN_GEREKCESI


async def metin_cikar(dosya: Dosya) -> tuple[str, str | None]:
    """Dosyayi diskten okuyup metnini cikarir: `(metin, gerekce)`.

    Ikinci deger bir katalog anahtaridir (`dosya_metni_cikarilamadi`) ya da
    metin basariyla cikarildiysa None.
    """
    try:
        icerik = Path(dosya.yol).read_bytes()
    except OSError:
        return "", METIN_GEREKCESI
    return icerik_metni(icerik, dosya.mime)


async def _org_slug(oturum: AsyncSession, org_id: int) -> str:
    slug = (
        await oturum.execute(sa.select(Organizasyon.slug).where(Organizasyon.id == org_id))
    ).scalar_one_or_none()
    return str(slug or f"org{org_id}")


async def dosya_kaydet(
    oturum: AsyncSession,
    *,
    org_id: int,
    kullanici_id: int | None,
    ad: str,
    mime: str,
    icerik: bytes,
) -> Dosya:
    """Icerigi diske yazar, metnini cikarip maskeler ve kaydi olusturur."""
    hedef_dizin = Path(ayarlar.dosya_dizini_yolu()) / await _org_slug(oturum, org_id)
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    hedef = hedef_dizin / uuid.uuid4().hex
    hedef.write_bytes(icerik)

    dosya = Dosya(
        org_id=org_id,
        kullanici_id=kullanici_id,
        ad=(ad or "dosya")[:300],
        mime=(mime or "application/octet-stream")[:160],
        boyut=len(icerik),
        sha256=hashlib.sha256(icerik).hexdigest(),
        yol=hedef.as_posix(),
        metin="",
    )
    oturum.add(dosya)
    await oturum.flush()

    ham_metin, _gerekce = icerik_metni(icerik, dosya.mime)
    dosya.metin = await maskele_metin(oturum, ham_metin) if ham_metin else ""
    await oturum.flush()
    return dosya


async def dosya_getir(oturum: AsyncSession, org_id: int, dosya_id: int) -> Dosya:
    """Organizasyon kapsamindaki dosyayi dondurur; baska org'un kaydi 404."""
    dosya = (
        await oturum.execute(
            sa.select(Dosya).where(Dosya.id == dosya_id, Dosya.org_id == org_id)
        )
    ).scalar_one_or_none()
    if dosya is None:
        raise Bulunamadi("bulunamadi", {"dosya_id": dosya_id})
    return dosya


def baytlari_oku(dosya: Dosya) -> bytes:
    """Diskteki ham icerigi okur (indirme ve ses cozumleme icin)."""
    try:
        return Path(dosya.yol).read_bytes()
    except OSError as hata:
        raise Bulunamadi(
            "bulunamadi", {"dosya_id": dosya.id, "neden": "icerik_diskte_yok"}
        ) from hata


async def icerik_oku(oturum: AsyncSession, org_id: int, dosya_id: int) -> tuple[Dosya, bytes]:
    """Kaydi ve ham baytlarini birlikte dondurur (org disi → 404)."""
    dosya = await dosya_getir(oturum, org_id, dosya_id)
    return dosya, baytlari_oku(dosya)


def diskten_sil(dosya: Dosya) -> None:
    """Diskteki kopyayi siler; kayit silindikten sonra cagrilir."""
    if not dosya.yol:
        return
    try:
        Path(dosya.yol).unlink(missing_ok=True)
    except OSError:  # pragma: no cover - disk izni/yaris durumu
        logger.warning("Dosya diskten silinemedi: %s", dosya.yol)


async def baglam_metni(
    oturum: AsyncSession, org_id: int, dosya_idleri: list[int], *, sinir: int
) -> str:
    """Verilen dosyalarin (maskeli) metnini birlestirir ve `sinir`da keser.

    Her dosya `--- <ad> ---` basligiyla eklenir; metni cikarilmamis dosyalar
    atlanir. Organizasyona ait olmayan bir id `Bulunamadi` (404) dogurur.
    """
    bloklar: list[str] = []
    for dosya_id in dosya_idleri:
        dosya = await dosya_getir(oturum, org_id, dosya_id)
        if not dosya.metin:
            continue
        bloklar.append(f"--- {dosya.ad} ---\n{dosya.metin}")
    return "\n".join(bloklar)[: max(0, int(sinir))]
