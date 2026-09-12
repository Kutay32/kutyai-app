"""Tohum verisi: varsayilan ayarlar, maskeleme kurallari, organizasyon, planlar.

Kullanim: `await tohumla()` uygulama acilirken ya da test kurulumunda cagrilir.
Idempotenttir; var olan kayitlari degistirmez.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from bdm_veritabani.modeller import (
    Ayar,
    MaskelemeKurali,
    Organizasyon,
    OrganizasyonDurumu,
    Plan,
    PostaSablonu,
)
from bdm_veritabani.oturum import oturum_fabrikasi

VARSAYILAN_AYARLAR: dict[str, object] = {
    "kurulum_tamam": False,
    "marka_adi": "KutyAI",
    "varsayilan_bdm_slug": None,
    "saklama_gun": 90,
    "maskeleme_aktif": True,
    "kayit_acik": True,
    "bakim_modu": False,
    "smtp_gonderen": "",
    "son_dogrulama_baglantisi": None,
    "son_sifirlama_baglantisi": None,
    "varsayilan_dil": "tr",
}

#: Varsayilan organizasyon (v1 kurulumlarinin baglandigi kiraci).
VARSAYILAN_ORG_SLUG = "varsayilan"
VARSAYILAN_ORG_AD = "Varsayılan Organizasyon"

MASKELEME_KURALLARI: tuple[tuple[str, str, int], ...] = (
    ("tckn", r"\b[1-9][0-9]{10}\b", 10),
    ("eposta", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", 20),
    ("telefon", r"(?:\+90|0)?[\s.\-]?\(?5[0-9]{2}\)?[\s.\-]?[0-9]{3}[\s.\-]?[0-9]{2}[\s.\-]?[0-9]{2}", 30),
    ("iban", r"\bTR[0-9]{2}[\s]?(?:[0-9]{4}[\s]?){5}[0-9]{2}\b", 40),
    ("kredi_karti", r"\b(?:[0-9][ \-]?){13,16}\b", 50),
)

PLANLAR: tuple[dict[str, object], ...] = (
    {
        "slug": "deneme",
        "ad": "Deneme",
        "aylik_fiyat_kurus": 0,
        "dahil_istek": 200,
        "dahil_token": 200_000,
        "ozellikler": {"destek": "topluluk", "rag": False, "sso": False},
    },
    {
        "slug": "baslangic",
        "ad": "Başlangıç",
        "aylik_fiyat_kurus": 99_000,
        "dahil_istek": 20_000,
        "dahil_token": 20_000_000,
        "ozellikler": {"destek": "e-posta", "rag": True, "sso": False},
    },
    {
        "slug": "kurumsal",
        "ad": "Kurumsal",
        "aylik_fiyat_kurus": 499_000,
        "dahil_istek": None,
        "dahil_token": None,
        "ozellikler": {"destek": "öncelikli", "rag": True, "sso": True},
    },
)

POSTA_SABLONLARI: tuple[dict[str, str], ...] = (
    {
        "kod": "dogrulama",
        "dil": "tr",
        "konu": "{{marka}} — E-posta adresinizi doğrulayın",
        "govde_metin": "Merhaba {{ad}},\n\nHesabınızı doğrulamak için bağlantıyı açın:\n{{baglanti}}\n\nBağlantı 24 saat geçerlidir.",
        "govde_html": "<p>Merhaba {{ad}},</p><p>Hesabınızı doğrulamak için <a href=\"{{baglanti}}\">bu bağlantıyı</a> açın.</p><p>Bağlantı 24 saat geçerlidir.</p>",
    },
    {
        "kod": "dogrulama",
        "dil": "en",
        "konu": "{{marka}} — Verify your email address",
        "govde_metin": "Hello {{ad}},\n\nOpen this link to verify your account:\n{{baglanti}}\n\nThe link is valid for 24 hours.",
        "govde_html": "<p>Hello {{ad}},</p><p>Open <a href=\"{{baglanti}}\">this link</a> to verify your account.</p><p>The link is valid for 24 hours.</p>",
    },
    {
        "kod": "sifirlama",
        "dil": "tr",
        "konu": "{{marka}} — Parola sıfırlama",
        "govde_metin": "Merhaba {{ad}},\n\nParolanızı sıfırlamak için bağlantıyı açın:\n{{baglanti}}\n\nBağlantı 2 saat geçerlidir. Bu isteği siz yapmadıysanız yok sayın.",
        "govde_html": "<p>Merhaba {{ad}},</p><p>Parolanızı sıfırlamak için <a href=\"{{baglanti}}\">bu bağlantıyı</a> açın.</p><p>Bağlantı 2 saat geçerlidir.</p>",
    },
    {
        "kod": "sifirlama",
        "dil": "en",
        "konu": "{{marka}} — Password reset",
        "govde_metin": "Hello {{ad}},\n\nOpen this link to reset your password:\n{{baglanti}}\n\nThe link is valid for 2 hours.",
        "govde_html": "<p>Hello {{ad}},</p><p>Open <a href=\"{{baglanti}}\">this link</a> to reset your password.</p><p>The link is valid for 2 hours.</p>",
    },
    {
        "kod": "davet",
        "dil": "tr",
        "konu": "{{marka}} — {{organizasyon}} ekibine davetlisiniz",
        "govde_metin": "Merhaba,\n\n{{davet_eden}} sizi {{organizasyon}} organizasyonuna davet etti.\nKatılmak için: {{baglanti}}",
        "govde_html": "<p>Merhaba,</p><p>{{davet_eden}} sizi <strong>{{organizasyon}}</strong> organizasyonuna davet etti.</p><p><a href=\"{{baglanti}}\">Katılmak için tıklayın</a></p>",
    },
    {
        "kod": "davet",
        "dil": "en",
        "konu": "{{marka}} — You are invited to {{organizasyon}}",
        "govde_metin": "Hello,\n\n{{davet_eden}} invited you to the {{organizasyon}} organization.\nJoin here: {{baglanti}}",
        "govde_html": "<p>Hello,</p><p>{{davet_eden}} invited you to <strong>{{organizasyon}}</strong>.</p><p><a href=\"{{baglanti}}\">Join here</a></p>",
    },
    {
        "kod": "kota_uyarisi",
        "dil": "tr",
        "konu": "{{marka}} — Kota uyarısı",
        "govde_metin": "{{organizasyon}} organizasyonunda kotanızın %{{yuzde}} kadarını kullandınız.",
        "govde_html": "<p><strong>{{organizasyon}}</strong> organizasyonunda kotanızın %{{yuzde}} kadarını kullandınız.</p>",
    },
    {
        "kod": "kota_uyarisi",
        "dil": "en",
        "konu": "{{marka}} — Quota warning",
        "govde_metin": "The {{organizasyon}} organization has used {{yuzde}}% of its quota.",
        "govde_html": "<p><strong>{{organizasyon}}</strong> has used {{yuzde}}% of its quota.</p>",
    },
    {
        "kod": "fatura",
        "dil": "tr",
        "konu": "{{marka}} — Fatura #{{fatura_no}}",
        "govde_metin": "Merhaba {{ad}},\n\n{{donem}} dönemi faturanız hazır: {{tutar}}.\nFaturayı görüntülemek için: {{baglanti}}",
        "govde_html": "<p>Merhaba {{ad}},</p><p>{{donem}} dönemi faturanız hazır: <strong>{{tutar}}</strong>.</p><p><a href=\"{{baglanti}}\">Faturayı görüntüle</a></p>",
    },
    {
        "kod": "fatura",
        "dil": "en",
        "konu": "{{marka}} — Invoice #{{fatura_no}}",
        "govde_metin": "Hello {{ad}},\n\nYour invoice for {{donem}} is ready: {{tutar}}.\nView it here: {{baglanti}}",
        "govde_html": "<p>Hello {{ad}},</p><p>Your invoice for {{donem}} is ready: <strong>{{tutar}}</strong>.</p><p><a href=\"{{baglanti}}\">View invoice</a></p>",
    },
    {
        "kod": "hosgeldin",
        "dil": "tr",
        "konu": "{{marka}} ailesine hoş geldiniz",
        "govde_metin": "Merhaba {{ad}},\n\nHesabınız hazır. Sohbete başlamak için: {{baglanti}}",
        "govde_html": "<p>Merhaba {{ad}},</p><p>Hesabınız hazır. <a href=\"{{baglanti}}\">Sohbete başlayın</a></p>",
    },
    {
        "kod": "hosgeldin",
        "dil": "en",
        "konu": "Welcome to {{marka}}",
        "govde_metin": "Hello {{ad}},\n\nYour account is ready. Start chatting: {{baglanti}}",
        "govde_html": "<p>Hello {{ad}},</p><p>Your account is ready. <a href=\"{{baglanti}}\">Start chatting</a></p>",
    },
)


async def tohumla(oturum: AsyncSession | None = None) -> None:
    """Varsayilan ayar, maskeleme kurali, organizasyon, plan ve sablonlari ekler."""
    if oturum is not None:
        await _uygula(oturum)
        return
    async with oturum_fabrikasi()() as kendi_oturum:
        await _uygula(kendi_oturum)
        await kendi_oturum.commit()


async def varsayilan_organizasyon(oturum: AsyncSession) -> Organizasyon:
    """Varsayilan organizasyonu getirir (yoksa olusturur)."""
    from bdm_veritabani.oturum import varsayilan_org_id_ata

    mevcut = (
        await oturum.execute(
            sa.select(Organizasyon).where(Organizasyon.slug == VARSAYILAN_ORG_SLUG)
        )
    ).scalar_one_or_none()
    if mevcut is not None:
        varsayilan_org_id_ata(mevcut.id)
        return mevcut
    organizasyon = Organizasyon(
        ad=VARSAYILAN_ORG_AD, slug=VARSAYILAN_ORG_SLUG, durum=OrganizasyonDurumu.aktif
    )
    oturum.add(organizasyon)
    await oturum.flush()
    varsayilan_org_id_ata(organizasyon.id)
    return organizasyon


async def _uygula(oturum: AsyncSession) -> None:
    mevcut_ayarlar = set((await oturum.execute(sa.select(Ayar.anahtar))).scalars().all())
    for anahtar, deger in VARSAYILAN_AYARLAR.items():
        if anahtar not in mevcut_ayarlar:
            oturum.add(Ayar(anahtar=anahtar, deger=deger))

    mevcut_kurallar = set(
        (await oturum.execute(sa.select(MaskelemeKurali.ad))).scalars().all()
    )
    for ad, desen, sira in MASKELEME_KURALLARI:
        if ad not in mevcut_kurallar:
            oturum.add(MaskelemeKurali(ad=ad, desen=desen, sira=sira, etkin=True))

    organizasyon = await varsayilan_organizasyon(oturum)

    mevcut_planlar = set((await oturum.execute(sa.select(Plan.slug))).scalars().all())
    for plan in PLANLAR:
        if plan["slug"] not in mevcut_planlar:
            oturum.add(Plan(**plan))

    mevcut_sablonlar = set(
        (await oturum.execute(sa.select(PostaSablonu.kod, PostaSablonu.dil))).all()
    )
    for sablon in POSTA_SABLONLARI:
        if (sablon["kod"], sablon["dil"]) not in mevcut_sablonlar:
            oturum.add(PostaSablonu(org_id=organizasyon.id, **sablon))

    await oturum.flush()
