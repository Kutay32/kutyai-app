"""SAML 2.0 doğrulama testleri (spec §7).

Test, gerçek bir IdP taklidi kurar: RSA anahtarı + kendi kendine imzalı
sertifika üretilir, SAML yanıtı `signxml` ile GERÇEKTEN imzalanır. Böylece
imza, Audience, süre, InResponseTo, replay ve XSW denetimleri canlı sınanır.
"""

from __future__ import annotations

import base64
import zlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from signxml import XMLSigner, methods

from arkauc.app.cekirdek.hatalar import JetonGecersiz
from arkauc.app.servisler import sso_saml
from bdm_veritabani.modeller import SsoSaglayici, SsoTuru

ACS = "http://localhost:8000/api/v1/sso/test-org/test-idp/saml/acs"
SP_ENTITY = "kutyai-test-sp"
IDP_ENTITY = "https://idp.ornek.local/metadata"


@pytest.fixture(scope="module")
def anahtar_cifti():
    anahtar = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    konu = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "idp.ornek.local")])
    sertifika = (
        x509.CertificateBuilder()
        .subject_name(konu)
        .issuer_name(konu)
        .public_key(anahtar.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(anahtar, hashes.SHA256())
    )
    ozel_pem = anahtar.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    genel_pem = sertifika.public_bytes(serialization.Encoding.PEM).decode()
    return ozel_pem, genel_pem


@pytest.fixture
def saglayici(anahtar_cifti):
    _ozel, genel = anahtar_cifti
    return SsoSaglayici(
        org_id=1,
        tur=SsoTuru.saml,
        ad="Test SAML IdP",
        slug="test-idp",
        etkin=True,
        ayarlar={
            "sp_entity_id": SP_ENTITY,
            "idp_imza_sertifikasi": genel,
            "eposta_ozniteligi": "email",
            "ad_ozniteligi": "displayName",
        },
    )


def _iso(zaman: datetime) -> str:
    return zaman.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _yanit_uret(
    *,
    eposta: str = "saml.kullanici@ornek.local",
    ad: str = "SAML Kullanıcı",
    assertion_id: str = "_a1",
    audience: str = SP_ENTITY,
    destination: str = ACS,
    in_response_to: str | None = None,
    not_before_delta: int = -60,
    not_on_or_after_delta: int = 300,
    subject_not_on_or_after_delta: int | None = None,
) -> str:
    an = datetime.now(timezone.utc)
    irt = f' InResponseTo="{in_response_to}"' if in_response_to else ""
    konu_son = (
        an + timedelta(seconds=subject_not_on_or_after_delta)
        if subject_not_on_or_after_delta is not None
        else an + timedelta(seconds=not_on_or_after_delta)
    )
    return f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" \
xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_r1" Version="2.0" \
IssueInstant="{_iso(an)}" Destination="{destination}"{irt}>
  <saml:Issuer>{IDP_ENTITY}</saml:Issuer>
  <samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>
  <saml:Assertion ID="{assertion_id}" Version="2.0" IssueInstant="{_iso(an)}">
    <saml:Issuer>{IDP_ENTITY}</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{eposta}</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData NotOnOrAfter="{_iso(konu_son)}" \
Recipient="{ACS}"{irt}/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    <saml:Conditions NotBefore="{_iso(an + timedelta(seconds=not_before_delta))}" \
NotOnOrAfter="{_iso(an + timedelta(seconds=not_on_or_after_delta))}">
      <saml:AudienceRestriction><saml:Audience>{audience}</saml:Audience></saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AuthnStatement AuthnInstant="{_iso(an)}" SessionIndex="_s1">
      <saml:AuthnContext>
        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>
      </saml:AuthnContext>
    </saml:AuthnStatement>
    <saml:AttributeStatement>
      <saml:Attribute Name="email"><saml:AttributeValue>{eposta}</saml:AttributeValue></saml:Attribute>
      <saml:Attribute Name="displayName"><saml:AttributeValue>{ad}</saml:AttributeValue></saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""


def _imzala(xml_metni: str, ozel_anahtar: str, sertifika: str, *, hedef: str = "Response") -> str:
    from lxml import etree

    kok = etree.fromstring(xml_metni.encode())
    imzalanacak = kok
    if hedef == "Assertion":
        imzalanacak = kok.find(
            "{urn:oasis:names:tc:SAML:2.0:assertion}Assertion"
        )
    imzalayici = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )
    imzali = imzalayici.sign(imzalanacak, key=ozel_anahtar, cert=sertifika)
    return etree.tostring(imzali, encoding="unicode")


@pytest.fixture(autouse=True)
def tekrar_temizle():
    sso_saml.tekrar_kumesini_temizle()
    yield
    sso_saml.tekrar_kumesini_temizle()


def test_gecerli_yanit_dogrulanir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(), ozel, sertifika)
    bilgi = sso_saml.yanit_dogrula(
        saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
    )
    assert bilgi["dis_id"] == "saml.kullanici@ornek.local"
    assert bilgi["eposta"] == "saml.kullanici@ornek.local"
    assert bilgi["ad"] == "SAML Kullanıcı"


def test_imzasiz_yanit_reddedilir(saglayici):
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=_yanit_uret(), acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.kod == "saml_yanit_gecersiz"
    assert hata.value.ayrinti["neden"] == "imza_yok"


def test_yanlis_sertifikayla_imzalanan_yanit_reddedilir(saglayici):
    baska = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    konu = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sahte.local")])
    sahte_sertifika = (
        x509.CertificateBuilder()
        .subject_name(konu)
        .issuer_name(konu)
        .public_key(baska.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .sign(baska, hashes.SHA256())
    )
    ozel_pem = baska.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    genel_pem = sahte_sertifika.public_bytes(serialization.Encoding.PEM).decode()
    imzali = _imzala(_yanit_uret(), ozel_pem, genel_pem)

    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.ayrinti["neden"] == "imza"


def test_audience_uyusmazligi_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(audience="baska-sp"), ozel, sertifika)
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.ayrinti["neden"] == "audience"


def test_destination_uyusmazligi_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(destination="http://baska.local/acs"), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.ayrinti["neden"] == "destination"


def test_suresi_gecmis_yanit_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(not_before_delta=-600, not_on_or_after_delta=-300), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.ayrinti["neden"] in {"not_on_or_after", "subject_suresi"}


def test_henuz_gecerli_degil_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(not_before_delta=600, not_on_or_after_delta=1200), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.ayrinti["neden"] == "not_before"


def test_in_response_to_uyusmazligi_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(in_response_to="_baska"), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id="_beklenen"
        )
    assert hata.value.ayrinti["neden"] == "in_response_to"


def test_ayni_assertion_ikinci_kez_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(assertion_id="_tek"), ozel, sertifika)
    ilk = sso_saml.yanit_dogrula(
        saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
    )
    assert ilk["eposta"]

    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert hata.value.kod == "saml_tekrar_oynatma"


def test_birden_fazla_assertion_reddedilir(saglayici, anahtar_cifti):
    """Doğrulanmış ağaçta birden fazla Assertion varsa belirsizlik kabul edilmez.

    İmza geçerliyken bu durum ancak IdP iki Assertion imzalarsa oluşur; bu
    yüzden koruma birim düzeyinde sınanır (imza sonrası ağaç elle kurulur).
    """
    from lxml import etree

    ns = "{urn:oasis:names:tc:SAML:2.0:assertion}"
    _ozel, sertifika = anahtar_cifti
    imzali = etree.fromstring(_imzala(_yanit_uret(assertion_id="_cok"), _ozel, sertifika).encode())
    ilk = imzali.find(f"{ns}Assertion")
    kopya = etree.fromstring(etree.tostring(ilk))
    kopya.set("ID", "_kopya")
    imzali.append(kopya)

    with pytest.raises(JetonGecersiz) as hata:
        sso_saml._assertion_sec(imzali)
    assert hata.value.ayrinti["neden"] == "assertion_sayisi"


def test_xsw_sahte_assertion_yok_sayilir(saglayici, anahtar_cifti):
    """İmzasız sahte Assertion eklenirse doğrulanmış (imzalı) olan kullanılır.

    Sahte Assertion, imzalı olandan ÖNCE yerleştirilir; naif "ilk Assertion"
    mantığı aldatılırdı. İmzalı Assertion bayt bayt korunur (yeniden
    serileştirme C14N özetini bozardı).
    """
    ozel, sertifika = anahtar_cifti
    gercek = _yanit_uret(eposta="gercek@ornek.local", assertion_id="_gercek", ad="Gerçek")
    imzali_assertion = _imzala(gercek, ozel, sertifika, hedef="Assertion")
    assert "_gercek" in imzali_assertion

    sahte = _yanit_uret(eposta="saldirgan@kotu.local", assertion_id="_sahte", ad="Sahte")
    from lxml import etree

    ns = "{urn:oasis:names:tc:SAML:2.0:assertion}"
    sahte_kok = etree.fromstring(sahte.encode())
    sahte_assertion = etree.tostring(sahte_kok.find(f"{ns}Assertion"), encoding="unicode")

    sarici = (
        '<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_r1" Version="2.0">'
        + sahte_assertion
        + imzali_assertion
        + "</samlp:Response>"
    )

    bilgi = sso_saml.yanit_dogrula(
        saglayici, saml_yaniti=sarici, acs_url=ACS, beklenen_istek_id=None
    )
    assert bilgi["eposta"] == "gercek@ornek.local"
    assert bilgi["ad"] == "Gerçek"
    assert "saldirgan" not in bilgi["eposta"]


def test_authn_istegi_uret_ve_coz(saglayici):
    saglayici.ayarlar = {**saglayici.ayarlar, "idp_sso_url": "https://idp.ornek.local/sso"}
    url, istek_id = sso_saml.authn_istegi_uret(
        saglayici, acs_url=ACS, relay_state="durum-123"
    )
    assert istek_id.startswith("_")
    ayrisan = urlparse(url)
    assert ayrisan.geturl().startswith("https://idp.ornek.local/sso?SAMLRequest=")
    parametreler = parse_qs(ayrisan.query)
    assert parametreler["RelayState"] == ["durum-123"]

    ham = base64.b64decode(unquote(parametreler["SAMLRequest"][0]))
    xml = zlib.decompress(ham, -15).decode()
    assert istek_id in xml
    assert f'Destination="https://idp.ornek.local/sso"' in xml
    assert f'AssertionConsumerServiceURL="{ACS}"' in xml
    assert f"<saml:Issuer>{SP_ENTITY}</saml:Issuer>" in xml


def test_sertifikasiz_saglayici_reddedilir(anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    saglayici = SsoSaglayici(
        org_id=1, tur=SsoTuru.saml, ad="Sertifikasız", slug="x", ayarlar={}
    )
    imzali = _imzala(_yanit_uret(), ozel, sertifika)
    with pytest.raises(Exception) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=None
        )
    assert getattr(hata.value, "kod", "") == "sso_yapilandirilmamis"


def test_xxe_varlik_genisletmesi_engellenir(saglayici):
    kotu = """<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///C:/Windows/win.ini">]>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" \
xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_r1" Version="2.0">
  <saml:Assertion ID="_a1" Version="2.0"><saml:Subject>
    <saml:NameID>&xxe;</saml:NameID></saml:Subject></saml:Assertion>
</samlp:Response>"""
    with pytest.raises(JetonGecersiz):
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=kotu, acs_url=ACS, beklenen_istek_id=None
        )
