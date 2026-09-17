"""SAML 2.0 doğrulama testleri (spec §7).

Test, gerçek bir IdP taklidi kurar: RSA anahtarı + kendi kendine imzalı
sertifika üretilir, SAML yanıtı `signxml` ile GERÇEKTEN imzalanır. Böylece
imza, Audience, süre, InResponseTo, replay ve XSW denetimleri canlı sınanır.
API düzeyinde de `/saml/baslat` → `/saml/acs` akışı sınanır: imzalı
yönlendirme parametreleri, `RelayState` (state) ve `InResponseTo` bağlaması.
"""

from __future__ import annotations

import base64
import logging
import zlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from signxml import XMLSigner, methods

from arkauc.app.cekirdek.ayarlar import ayarlar
from arkauc.app.cekirdek.hatalar import Cakisma, GecersizIstek, JetonGecersiz
from arkauc.app.servisler import sso_oidc, sso_saml
from bdm_veritabani.modeller import SsoSaglayici, SsoTuru
from bdm_veritabani.oturum import oturum_fabrikasi

ACS = "http://localhost:8000/api/v1/sso/test-org/test-idp/saml/acs"
SP_ENTITY = "kutyai-test-sp"
IDP_ENTITY = "https://idp.ornek.local/metadata"
#: Akışı başlatan `AuthnRequest` kimliği; yanıtlar `InResponseTo` ile buna bağlanır.
ISTEK_ID = "_beklenen"


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


@pytest.fixture(scope="module")
def sp_anahtar_cifti():
    """SP `AuthnRequest` imza anahtarı: (PEM özel anahtar, açık anahtar)."""
    anahtar = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ozel_pem = anahtar.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return ozel_pem, anahtar.public_key()


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
    recipient: str = ACS,
    in_response_to: str | None = ISTEK_ID,
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
Recipient="{recipient}"{irt}/>
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


def _oznitelik_sil(xml_metni: str, etiket: str, oznitelik: str) -> str:
    """Verilen SAML/SAMLp düğümlerinden bir özniteliği siler (negatif testler)."""
    from lxml import etree

    kok = etree.fromstring(xml_metni.encode())
    for ns in (
        "{urn:oasis:names:tc:SAML:2.0:assertion}",
        "{urn:oasis:names:tc:SAML:2.0:protocol}",
    ):
        for dugum in kok.iter(f"{ns}{etiket}"):
            dugum.attrib.pop(oznitelik, None)
    return etree.tostring(kok, encoding="unicode")


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
def tekrar_temizle(monkeypatch):
    """Tekrar/state kümeleri ve sahte IdP konakları için SSO yerel izni."""
    monkeypatch.setattr(ayarlar, "sso_yerel_izin", True)
    sso_saml.tekrar_kumesini_temizle()
    sso_oidc.durum_kumesini_temizle()
    yield
    sso_saml.tekrar_kumesini_temizle()
    sso_oidc.durum_kumesini_temizle()


def _yonlendirme_imzasini_dogrula(url: str, genel_anahtar) -> str:
    """Yönlendirmedeki `SigAlg`+`Signature` parametrelerini doğrular.

    İmza, sorgu dizesinde görünen `SAMLRequest=..&RelayState=..&SigAlg=..`
    parçası üzerinden RSA-SHA256 ile hesaplanmış olmalıdır; `SigAlg`
    çözümü döner.
    """
    ayrisan = urlparse(url)
    imzalanan, ayirici, imza_kodlu = ayrisan.query.partition("&Signature=")
    assert ayirici, "Signature parametresi yok"
    genel_anahtar.verify(
        base64.b64decode(unquote(imza_kodlu), validate=True),
        imzalanan.encode("ascii"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return parse_qs(imzalanan)["SigAlg"][0]


async def _api_saglayici_ekle(
    org_id: int, *, ayarlar: dict[str, str], slug: str = "test-saml"
) -> SsoSaglayici:
    async with oturum_fabrikasi()() as oturum:
        saglayici = SsoSaglayici(
            org_id=org_id,
            tur=SsoTuru.saml,
            ad="API Test SAML IdP",
            slug=slug,
            etkin=True,
            ayarlar=ayarlar,
        )
        oturum.add(saglayici)
        await oturum.commit()
        await oturum.refresh(saglayici)
        return saglayici


def test_gecerli_yanit_dogrulanir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(), ozel, sertifika)
    bilgi = sso_saml.yanit_dogrula(
        saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
    )
    assert bilgi["dis_id"] == "saml.kullanici@ornek.local"
    assert bilgi["eposta"] == "saml.kullanici@ornek.local"
    assert bilgi["ad"] == "SAML Kullanıcı"


def test_imzasiz_yanit_reddedilir(saglayici):
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=_yanit_uret(), acs_url=ACS, beklenen_istek_id=ISTEK_ID
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
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "imza"


def test_audience_uyusmazligi_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(audience="baska-sp"), ozel, sertifika)
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "audience"


def test_destination_uyusmazligi_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(destination="http://baska.local/acs"), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "destination"


def test_suresi_gecmis_yanit_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(not_before_delta=-600, not_on_or_after_delta=-300), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] in {"not_on_or_after", "subject_suresi"}


def test_henuz_gecerli_degil_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(not_before_delta=600, not_on_or_after_delta=1200), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "not_before"


def test_in_response_to_uyusmazligi_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(
        _yanit_uret(in_response_to="_baska"), ozel, sertifika
    )
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "in_response_to"


def test_in_response_to_yoksa_reddedilir(saglayici, anahtar_cifti):
    """Başlatılmış akışta yanıt `InResponseTo` taşımak zorundadır (spec §7)."""
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(in_response_to=None), ozel, sertifika)
    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "in_response_to"


def test_ayni_assertion_ikinci_kez_reddedilir(saglayici, anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_yanit_uret(assertion_id="_tek"), ozel, sertifika)
    ilk = sso_saml.yanit_dogrula(
        saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
    )
    assert ilk["eposta"]

    with pytest.raises(Cakisma) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.kod == "saml_tekrar_oynatma"
    assert hata.value.durum_kodu == 409


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
        saglayici, saml_yaniti=sarici, acs_url=ACS, beklenen_istek_id=ISTEK_ID
    )
    assert bilgi["eposta"] == "gercek@ornek.local"
    assert bilgi["ad"] == "Gerçek"
    assert "saldirgan" not in bilgi["eposta"]


def test_authn_istegi_uret_ve_coz(saglayici, caplog):
    caplog.set_level(logging.WARNING, logger="kutyai.sso.saml")
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

    # `sp_imza_anahtari` yoksa imzasız üretilir ve durum uyarı olarak loglanır.
    assert "SigAlg" not in parametreler and "Signature" not in parametreler
    assert any(kayit.levelno == logging.WARNING for kayit in caplog.records)


def test_imzali_authn_istegi_sigalg_ve_imza(saglayici, sp_anahtar_cifti):
    """`sp_imza_anahtari` tanımlıyken imza, URL'de görünen dizi üzerinden üretilir."""
    sp_ozel, sp_genel = sp_anahtar_cifti
    saglayici.ayarlar = {
        **saglayici.ayarlar,
        "idp_sso_url": "https://idp.ornek.local/sso",
        "sp_imza_anahtari": sp_ozel,
    }
    url, istek_id = sso_saml.authn_istegi_uret(
        saglayici, acs_url=ACS, relay_state="durum-123", istek_id="_sabit"
    )
    assert istek_id == "_sabit"

    sig_alg = _yonlendirme_imzasini_dogrula(url, sp_genel)
    assert sig_alg == "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"

    ayrisan = urlparse(url)
    imzalanan, _, _imza = ayrisan.query.partition("&Signature=")
    parametreler = parse_qs(imzalanan)
    assert imzalanan.startswith("SAMLRequest=")
    assert parametreler["RelayState"] == ["durum-123"]
    xml = zlib.decompress(base64.b64decode(parametreler["SAMLRequest"][0]), -15).decode()
    assert istek_id in xml


def test_gecersiz_sp_imza_anahtari_reddedilir(saglayici):
    """Tanımlı ama yüklenemeyen anahtar sessizce imzasız üretime düşmez."""
    saglayici.ayarlar = {
        **saglayici.ayarlar,
        "idp_sso_url": "https://idp.ornek.local/sso",
        "sp_imza_anahtari": "bu bir PEM değil",
    }
    with pytest.raises(GecersizIstek) as hata:
        sso_saml.authn_istegi_uret(saglayici, acs_url=ACS, relay_state="durum")
    assert hata.value.kod == "sso_yapilandirilmamis"
    assert hata.value.ayrinti["alan"] == "sp_imza_anahtari"


def test_sertifikasiz_saglayici_reddedilir(anahtar_cifti):
    ozel, sertifika = anahtar_cifti
    saglayici = SsoSaglayici(
        org_id=1, tur=SsoTuru.saml, ad="Sertifikasız", slug="x", ayarlar={}
    )
    imzali = _imzala(_yanit_uret(), ozel, sertifika)
    with pytest.raises(Exception) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert getattr(hata.value, "kod", "") == "sso_yapilandirilmamis"


@pytest.mark.parametrize(
    ("etiket", "oznitelik", "neden"),
    [
        ("Conditions", "NotOnOrAfter", "sure_yok"),
        ("SubjectConfirmationData", "NotOnOrAfter", "sure_yok"),
        ("SubjectConfirmationData", "Recipient", "recipient"),
        ("Response", "Destination", "destination"),
    ],
)
def test_zorunlu_alanlar_yoksa_reddedilir(saglayici, anahtar_cifti, etiket, oznitelik, neden):
    """SEC-SAML-002: süre/alıcı alanlarının yokluğu da reddedilir (fail-closed)."""
    ozel, sertifika = anahtar_cifti
    imzali = _imzala(_oznitelik_sil(_yanit_uret(), etiket, oznitelik), ozel, sertifika)

    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.kod == "saml_yanit_gecersiz"
    assert hata.value.ayrinti["neden"] == neden


def test_subject_confirmation_yoksa_reddedilir(saglayici, anahtar_cifti):
    """SEC-SAML-002: `SubjectConfirmationData` yoksa süre/alıcı denetimi yapılamaz."""
    from lxml import etree

    ns = "{urn:oasis:names:tc:SAML:2.0:assertion}"
    ozel, sertifika = anahtar_cifti
    kok = etree.fromstring(_yanit_uret().encode())
    assertion = kok.find(f"{ns}Assertion")
    onay = assertion.find(f"{ns}Subject")
    onay.remove(onay.find(f"{ns}SubjectConfirmation"))
    imzali = _imzala(etree.tostring(kok, encoding="unicode"), ozel, sertifika)

    with pytest.raises(JetonGecersiz) as hata:
        sso_saml.yanit_dogrula(
            saglayici, saml_yaniti=imzali, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )
    assert hata.value.ayrinti["neden"] == "subject_confirmation"


def test_http_idp_sso_url_reddedilir(saglayici, monkeypatch):
    """SEC-OIDC-001: SAML IdP adresi `https` olmalıdır (yerel izin kapalıyken)."""
    monkeypatch.setattr(ayarlar, "sso_yerel_izin", False)
    saglayici.ayarlar = {**saglayici.ayarlar, "idp_sso_url": "http://idp.ornek.local/sso"}
    with pytest.raises(GecersizIstek) as hata:
        sso_saml.authn_istegi_uret(saglayici, acs_url=ACS, relay_state="durum")
    assert hata.value.kod == "sso_yapilandirilmamis"
    assert hata.value.ayrinti["alan"] == "idp_sso_url"


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
            saglayici, saml_yaniti=kotu, acs_url=ACS, beklenen_istek_id=ISTEK_ID
        )


# -- API düzeyi: /saml/baslat → /saml/acs ---------------------------------------


async def test_saml_baslat_302_ve_imzali_authn_istegi(
    istemci, yardimci, anahtar_cifti, sp_anahtar_cifti
):
    """Spec §7: `GET .../saml/baslat` → 302 + imzalı `AuthnRequest` + `RelayState`."""
    _ozel_idp, sertifika = anahtar_cifti
    sp_ozel, sp_genel = sp_anahtar_cifti
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _api_saglayici_ekle(
        organizasyon.id,
        ayarlar={
            "idp_sso_url": "https://idp.ornek.local/sso",
            "idp_imza_sertifikasi": sertifika,
            "sp_entity_id": SP_ENTITY,
            "sp_imza_anahtari": sp_ozel,
        },
    )

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/baslat",
        follow_redirects=False,
    )
    assert yanit.status_code == 302
    hedef = yanit.headers["location"]
    assert hedef.startswith("https://idp.ornek.local/sso?SAMLRequest=")

    parametreler = parse_qs(urlparse(hedef).query)
    from arkauc.app.servisler import sso_oidc

    govde = sso_oidc.state_coz(parametreler["RelayState"][0])
    assert govde["sid"] == saglayici.id

    xml = zlib.decompress(base64.b64decode(parametreler["SAMLRequest"][0]), -15).decode()
    assert f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/acs" in xml
    assert _yonlendirme_imzasini_dogrula(hedef, sp_genel) == (
        "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    )


async def test_baslat_geriye_uyumlu_saml_dondurur(istemci, yardimci, anahtar_cifti):
    """Geriye uyumluluk: `/baslat` SAML sağlayıcıda da `AuthnRequest` üretir."""
    _ozel, sertifika = anahtar_cifti
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _api_saglayici_ekle(
        organizasyon.id,
        ayarlar={
            "idp_sso_url": "https://idp.ornek.local/sso",
            "idp_imza_sertifikasi": sertifika,
            "sp_entity_id": SP_ENTITY,
        },
    )

    yanit = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/baslat",
        follow_redirects=False,
    )
    assert yanit.status_code == 302
    parametreler = parse_qs(urlparse(yanit.headers["location"]).query)
    assert parametreler["SAMLRequest"]
    assert parametreler["RelayState"]
    # İmza anahtarı tanımlı değil: parametreler imzasız üretilir.
    assert "SigAlg" not in parametreler and "Signature" not in parametreler


async def test_saml_acs_in_response_to_baglanir(istemci, yardimci, anahtar_cifti):
    """Spec §7: yanıt, başlatılan `AuthnRequest` kimliğine `InResponseTo` ile bağlanır."""
    from lxml import etree

    ozel, sertifika = anahtar_cifti
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _api_saglayici_ekle(
        organizasyon.id,
        ayarlar={
            "idp_sso_url": "https://idp.ornek.local/sso",
            "idp_imza_sertifikasi": sertifika,
            "sp_entity_id": SP_ENTITY,
            "eposta_ozniteligi": "email",
        },
    )
    acs_yolu = f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/acs"
    baslat_yolu = f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/baslat"

    async def _akis_baslat() -> tuple[str, str, str]:
        """(relay_state, istek_id, acs) — her ACS çağrısı taze bir akışla gelir."""
        baslat = await istemci.get(baslat_yolu, follow_redirects=False)
        parametreler = parse_qs(urlparse(baslat.headers["location"]).query)
        xml = zlib.decompress(base64.b64decode(parametreler["SAMLRequest"][0]), -15).decode()
        istek = etree.fromstring(xml.encode())
        return (
            parametreler["RelayState"][0],
            istek.get("ID"),
            istek.get("AssertionConsumerServiceURL"),
        )

    async def _acs_gonder(yanit_xml: str, relay_state: str | None):
        veri = {"SAMLResponse": base64.b64encode(yanit_xml.encode()).decode()}
        if relay_state is not None:
            veri["RelayState"] = relay_state
        return await istemci.post(acs_yolu, data=veri)

    # Doğru InResponseTo: akış tamamlanır (pozitif kontrol).
    relay_state, istek_id, acs = await _akis_baslat()
    dogru = _imzala(
        _yanit_uret(in_response_to=istek_id, destination=acs, recipient=acs),
        ozel,
        sertifika,
    )
    basarili = await _acs_gonder(dogru, relay_state)
    assert basarili.status_code == 200, basarili.text
    assert basarili.json()["erisim_jetonu"]
    assert basarili.json()["kullanici"]["eposta"] == "saml.kullanici@ornek.local"

    # Uyuşmayan InResponseTo reddedilir.
    relay_state, _istek_id, acs = await _akis_baslat()
    uyusmaz = _imzala(
        _yanit_uret(
            in_response_to="_baska", assertion_id="_a2", destination=acs, recipient=acs
        ),
        ozel,
        sertifika,
    )
    reddedildi = await _acs_gonder(uyusmaz, relay_state)
    assert reddedildi.status_code == 401
    assert reddedildi.json()["hata"]["kod"] == "saml_yanit_gecersiz"

    # Başlatılmış akışta `InResponseTo` hiç yoksa da reddedilir.
    relay_state, _istek_id, acs = await _akis_baslat()
    eksik = _imzala(
        _yanit_uret(
            in_response_to=None, assertion_id="_a3", destination=acs, recipient=acs
        ),
        ozel,
        sertifika,
    )
    eksik_yanit = await _acs_gonder(eksik, relay_state)
    assert eksik_yanit.status_code == 401
    assert eksik_yanit.json()["hata"]["kod"] == "saml_yanit_gecersiz"


async def test_saml_acs_relaystate_zorunlu(istemci, yardimci, anahtar_cifti):
    """SEC-SAML-001: `RelayState` yoksa ACS reddeder; InResponseTo denetimi atlanmaz."""
    from lxml import etree

    ozel, sertifika = anahtar_cifti
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _api_saglayici_ekle(
        organizasyon.id,
        ayarlar={
            "idp_sso_url": "https://idp.ornek.local/sso",
            "idp_imza_sertifikasi": sertifika,
            "sp_entity_id": SP_ENTITY,
            "eposta_ozniteligi": "email",
        },
    )
    acs_yolu = f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/acs"
    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/baslat",
        follow_redirects=False,
    )
    parametreler = parse_qs(urlparse(baslat.headers["location"]).query)
    xml = zlib.decompress(base64.b64decode(parametreler["SAMLRequest"][0]), -15).decode()
    acs = etree.fromstring(xml.encode()).get("AssertionConsumerServiceURL")
    imzali = _imzala(_yanit_uret(destination=acs, recipient=acs), ozel, sertifika)

    yanit = await istemci.post(
        acs_yolu, data={"SAMLResponse": base64.b64encode(imzali.encode()).decode()}
    )
    assert yanit.status_code == 400
    assert yanit.json()["hata"]["kod"] == "oidc_durum_gecersiz"


async def test_saml_acs_baska_saglayicinin_stateini_reddeder(istemci, yardimci, anahtar_cifti):
    """SEC-SAML-001: `RelayState` başka sağlayıcıya aitse ACS reddeder."""
    from lxml import etree

    ozel, sertifika = anahtar_cifti
    yonetici = await yardimci.yonetici()
    organizasyon = await yardimci.organizasyon(sahibi=yonetici)
    saglayici = await _api_saglayici_ekle(
        organizasyon.id,
        ayarlar={
            "idp_sso_url": "https://idp.ornek.local/sso",
            "idp_imza_sertifikasi": sertifika,
            "sp_entity_id": SP_ENTITY,
        },
    )
    acs_yolu = f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/acs"
    baslat = await istemci.get(
        f"/api/v1/sso/{organizasyon.slug}/{saglayici.slug}/saml/baslat",
        follow_redirects=False,
    )
    parametreler = parse_qs(urlparse(baslat.headers["location"]).query)
    xml = zlib.decompress(base64.b64decode(parametreler["SAMLRequest"][0]), -15).decode()
    istek = etree.fromstring(xml.encode())
    acs = istek.get("AssertionConsumerServiceURL")
    imzali = _imzala(
        _yanit_uret(in_response_to=istek.get("ID"), destination=acs, recipient=acs),
        ozel,
        sertifika,
    )
    yabanci_state = sso_oidc.state_uret(
        saglayici_id=saglayici.id + 1, nonce=istek.get("ID"), code_verifier="", donus=acs
    )

    yanit = await istemci.post(
        acs_yolu,
        data={
            "SAMLResponse": base64.b64encode(imzali.encode()).decode(),
            "RelayState": yabanci_state,
        },
    )
    assert yanit.status_code == 401
    assert yanit.json()["hata"]["kod"] == "oidc_durum_gecersiz"
