"""SAML 2.0 Web-Browser SSO doğrulaması (spec §7).

Güvenlik kuralları (pazarlık yok):
- XML-DSig imzası `signxml` ile doğrulanır; veri YALNIZ doğrulanmış düğümden
  okunur (XSW saldırılarına karşı).
- IdP sertifikası zorunludur; sertifikasız imza kabul edilmez.
- Audience, Destination/Recipient, zaman penceresi ve InResponseTo denetlenir.
- Aynı `Assertion ID` 10 dakika içinde reddedilir (tekrar oynatma).
"""

from __future__ import annotations

import base64
import logging
import time
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from lxml import etree
from signxml import XMLVerifier

from arkauc.app.cekirdek.hatalar import GecersizIstek, JetonGecersiz
from bdm_veritabani.modeller import SsoSaglayici

logger = logging.getLogger("kutyai.sso.saml")

SAML_NS = "urn:oasis:names:tc:SAML:2.0:assertion"
PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
ZAMAN_TOLERANSI_SN = 120
TEKRAR_ONLEME_SN = 600
GECERLI_ALGORITMALAR = (
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    "http://www.w3.org/2000/09/xmldsig#rsa-sha1",
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha384",
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512",
)

#: {assertion_id: gorulme_zamani}
_kullanilan_assertionlar: dict[str, float] = {}


def _ns(onek: str, yerel: str) -> str:
    return f"{{{SAML_NS}}}{yerel}" if onek == "saml" else f"{{{PROTOCOL_NS}}}{yerel}"


def _ayar(saglayici: SsoSaglayici, anahtar: str, varsayilan: str = "") -> str:
    return str((saglayici.ayarlar or {}).get(anahtar, varsayilan) or varsayilan)


def _sertifika(saglayici: SsoSaglayici) -> str:
    sertifika = _ayar(saglayici, "idp_imza_sertifikasi").strip()
    if not sertifika:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "idp_imza_sertifikasi"})
    if "BEGIN CERTIFICATE" not in sertifika:
        # Çıplak base64 gövdesini PEM'e sar
        govde = "".join(sertifika.split())
        satirlar = [govde[i : i + 64] for i in range(0, len(govde), 64)]
        sertifika = (
            "-----BEGIN CERTIFICATE-----\n"
            + "\n".join(satirlar)
            + "\n-----END CERTIFICATE-----\n"
        )
    return sertifika


def _guvenli_ayristir(xml_metni: str) -> etree._Element:
    """Varlık genişletme ve ağ erişimi kapalı ayrıştırma (XXE savunması)."""
    ayristirici = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False, huge_tree=False
    )
    try:
        return etree.fromstring(xml_metni.encode("utf-8"), parser=ayristirici)
    except etree.XMLSyntaxError as hata:
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "xml"}, kod="saml_yanit_gecersiz"
        ) from hata


def _tekrar_denetle(assertion_id: str, *, simdi: float | None = None) -> None:
    su_an = time.time() if simdi is None else simdi
    suresi_gecti = [
        anahtar
        for anahtar, zaman in _kullanilan_assertionlar.items()
        if su_an - zaman > TEKRAR_ONLEME_SN
    ]
    for anahtar in suresi_gecti:
        _kullanilan_assertionlar.pop(anahtar, None)
    if assertion_id and assertion_id in _kullanilan_assertionlar:
        raise JetonGecersiz(
            "saml_tekrar_oynatma", {"assertion_id": assertion_id}, kod="saml_tekrar_oynatma"
        )
    if assertion_id:
        _kullanilan_assertionlar[assertion_id] = su_an


def tekrar_kumesini_temizle() -> None:
    """Testler arası izolasyon."""
    _kullanilan_assertionlar.clear()


def authn_istegi_uret(
    saglayici: SsoSaglayici, *, acs_url: str, relay_state: str
) -> tuple[str, str]:
    """(yönlendirme_url, istek_id) — HTTP-Redirect bağlaması."""
    sso_url = _ayar(saglayici, "idp_sso_url")
    sp_entity = _ayar(saglayici, "sp_entity_id", acs_url)
    if not sso_url:
        raise GecersizIstek("sso_yapilandirilmamis", {"alan": "idp_sso_url"})

    istek_id = "_" + base64.urlsafe_b64encode(
        f"kutyai{int(time.time() * 1000)}".encode()
    ).decode().rstrip("=")
    istek = (
        f'<samlp:AuthnRequest xmlns:samlp="{PROTOCOL_NS}" xmlns:saml="{SAML_NS}" '
        f'ID="{istek_id}" Version="2.0" IssueInstant="{_iso(simdi())}" '
        f'Destination="{sso_url}" AssertionConsumerServiceURL="{acs_url}" '
        f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        f"<saml:Issuer>{sp_entity}</saml:Issuer>"
        f'<samlp:NameIDPolicy AllowCreate="true" '
        f'Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"/>'
        f"</samlp:AuthnRequest>"
    )
    sikistirilmis = zlib.compress(istek.encode("utf-8"))[2:-4]  # raw deflate
    kodlu = base64.b64encode(sikistirilmis).decode("ascii")
    url = (
        f"{sso_url}?SAMLRequest={quote(kodlu)}"
        f"&RelayState={quote(relay_state)}"
    )
    return url, istek_id


def simdi() -> datetime:
    return datetime.now(timezone.utc)


def _iso(zaman: datetime) -> str:
    return zaman.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _zaman_coz(metin: str | None) -> datetime | None:
    if not metin:
        return None
    try:
        temiz = metin.replace("Z", "+00:00")
        zaman = datetime.fromisoformat(temiz)
    except ValueError:
        return None
    if zaman.tzinfo is None:
        zaman = zaman.replace(tzinfo=timezone.utc)
    return zaman


def _imzali_dugum(ham: etree._Element, sertifika: str) -> etree._Element:
    """İmzalı düğümü doğrular ve döndürür (XSW savunması)."""
    yanit = ham if ham.tag == _ns("p", "Response") else None
    assertionlar = (
        [ham] if ham.tag == _ns("saml", "Assertion") else list(ham.iter(_ns("saml", "Assertion")))
    )
    if yanit is None and not assertionlar:
        raise JetonGecersiz("saml_yanit_gecersiz", {"neden": "kok"}, kod="saml_yanit_gecersiz")

    def _imzali_var(dügüm: etree._Element) -> bool:
        return dügüm.find("{http://www.w3.org/2000/09/xmldsig#}Signature") is not None

    hedef: etree._Element | None = None
    if yanit is not None and _imzali_var(yanit):
        hedef = yanit
    else:
        for aday in assertionlar:
            if _imzali_var(aday):
                hedef = aday
                break
    if hedef is None:
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "imza_yok"}, kod="saml_yanit_gecersiz"
        )

    try:
        # TÜM belge doğrulanır: detached imzalarda `#ID` referansı ancak tam
        # ağaç üzerinde çözülebilir. Sertifika sabitlendiği için saldırganın
        # eklediği imza/Assertion kabul edilmez.
        sonuc = XMLVerifier().verify(ham, x509_cert=sertifika)
    except Exception as hata:  # signxml hata sınıfları geniş
        logger.warning("SAML imzası doğrulanamadı: %s", hata)
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "imza"}, kod="saml_yanit_gecersiz"
        ) from hata

    dogrulanmis = sonuc.signed_xml
    if dogrulanmis is None:  # pragma: no cover - signxml sozlesmesi
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "imza_agaci"}, kod="saml_yanit_gecersiz"
        )
    algoritma = _imza_algoritmasi(dogrulanmis)
    if algoritma and algoritma not in GECERLI_ALGORITMALAR:
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "algoritma"}, kod="saml_yanit_gecersiz"
        )
    return dogrulanmis


def _imza_algoritmasi(dügüm: etree._Element) -> str:
    yol = ".//{http://www.w3.org/2000/09/xmldsig#}SignatureMethod"
    bulunan = dügüm.find(yol)
    if bulunan is None:
        return ""
    return bulunan.get("Algorithm", "")


def _assertion_sec(dogrulanmis: etree._Element) -> etree._Element:
    """Doğrulanmış ağaçtan Assertion'ı seçer (birden fazla varsa reddeder)."""
    if dogrulanmis.tag == _ns("saml", "Assertion"):
        return dogrulanmis
    assertionlar = list(dogrulanmis.iter(_ns("saml", "Assertion")))
    if len(assertionlar) != 1:
        raise JetonGecersiz(
            "saml_yanit_gecersiz",
            {"neden": "assertion_sayisi", "adet": len(assertionlar)},
            kod="saml_yanit_gecersiz",
        )
    return assertionlar[0]


def _kosul_metni(assertion: etree._Element, ad: str) -> str:
    bulunan = assertion.find(f".//{_ns('saml', ad)}")
    return bulunan.text.strip() if bulunan is not None and bulunan.text else ""


def yanit_dogrula(
    saglayici: SsoSaglayici,
    *,
    saml_yaniti: str,
    acs_url: str,
    beklenen_istek_id: str | None,
    simdi_an: datetime | None = None,
    tekrar_denetle: bool = True,
) -> dict[str, str]:
    """SAMLResponse'u doğrular ve kullanıcı alanlarını döndürür."""
    sertifika = _sertifika(saglayici)
    ham = _guvenli_ayristir(saml_yaniti)
    dogrulanmis = _imzali_dugum(ham, sertifika)

    yanit_dugumu = dogrulanmis if dogrulanmis.tag == _ns("p", "Response") else None
    if yanit_dugumu is not None:
        if beklenen_istek_id and yanit_dugumu.get("InResponseTo") not in (None, beklenen_istek_id):
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "in_response_to"}, kod="saml_yanit_gecersiz"
            )
        hedef = yanit_dugumu.get("Destination")
        if hedef and hedef != acs_url:
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "destination"}, kod="saml_yanit_gecersiz"
            )

    assertion = _assertion_sec(dogrulanmis)

    if beklenen_istek_id:
        gelen = assertion.get("InResponseTo") or (
            yanit_dugumu.get("InResponseTo") if yanit_dugumu is not None else None
        )
        if gelen and gelen != beklenen_istek_id:
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "in_response_to"}, kod="saml_yanit_gecersiz"
            )

    # Audience
    sp_entity = _ayar(saglayici, "sp_entity_id", acs_url)
    audience = assertion.find(f".//{_ns('saml', 'Audience')}")
    if audience is None or (audience.text or "").strip() != sp_entity:
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "audience"}, kod="saml_yanit_gecersiz"
        )

    # SubjectConfirmationData: Recipient + NotOnOrAfter
    onay = assertion.find(f".//{_ns('saml', 'SubjectConfirmationData')}")
    if onay is not None:
        alici = onay.get("Recipient")
        if alici and alici != acs_url:
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "recipient"}, kod="saml_yanit_gecersiz"
            )
        son = _zaman_coz(onay.get("NotOnOrAfter"))
        if son is not None and _su_an(simdi_an) > son + timedelta(seconds=ZAMAN_TOLERANSI_SN):
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "subject_suresi"}, kod="saml_yanit_gecersiz"
            )

    # Conditions: NotBefore / NotOnOrAfter
    kosullar = assertion.find(_ns("saml", "Conditions"))
    if kosullar is not None:
        baslangic = _zaman_coz(kosullar.get("NotBefore"))
        bitis = _zaman_coz(kosullar.get("NotOnOrAfter"))
        an = _su_an(simdi_an)
        if baslangic is not None and an + timedelta(seconds=ZAMAN_TOLERANSI_SN) < baslangic:
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "not_before"}, kod="saml_yanit_gecersiz"
            )
        if bitis is not None and an > bitis + timedelta(seconds=ZAMAN_TOLERANSI_SN):
            raise JetonGecersiz(
                "saml_yanit_gecersiz", {"neden": "not_on_or_after"}, kod="saml_yanit_gecersiz"
            )

    assertion_id = assertion.get("ID") or ""
    if tekrar_denetle:
        _tekrar_denetle(assertion_id)

    eposta_ozniteligi = _ayar(saglayici, "eposta_ozniteligi", "")
    eposta = ""
    if eposta_ozniteligi:
        for oznitelik in assertion.iter(_ns("saml", "Attribute")):
            if oznitelik.get("Name") == eposta_ozniteligi:
                deger = oznitelik.find(_ns("saml", "AttributeValue"))
                if deger is not None and deger.text:
                    eposta = deger.text.strip()
                    break

    konu = assertion.find(f".//{_ns('saml', 'NameID')}")
    name_id = (konu.text or "").strip() if konu is not None and konu.text else ""
    if not eposta and "@" in name_id:
        eposta = name_id

    ad = ""
    ad_ozniteligi = _ayar(saglayici, "ad_ozniteligi", "")
    if ad_ozniteligi:
        for oznitelik in assertion.iter(_ns("saml", "Attribute")):
            if oznitelik.get("Name") == ad_ozniteligi:
                deger = oznitelik.find(_ns("saml", "AttributeValue"))
                if deger is not None and deger.text:
                    ad = deger.text.strip()
                    break

    if not name_id and not eposta:
        raise JetonGecersiz(
            "saml_yanit_gecersiz", {"neden": "kimlik_yok"}, kod="saml_yanit_gecersiz"
        )

    return {"dis_id": name_id or eposta, "eposta": eposta.lower(), "ad": ad}


def _su_an(simdi_an: datetime | None) -> datetime:
    return simdi_an or simdi()


__all__: list[str] = [
    "authn_istegi_uret",
    "yanit_dogrula",
    "tekrar_kumesini_temizle",
    "GECERLI_ALGORITMALAR",
]
