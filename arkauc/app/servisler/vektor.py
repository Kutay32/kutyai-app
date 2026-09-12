"""Parcalama, vektor yazimi ve benzerlik aramasi (spec §5).

Arama iki yol kullanir ve yolu kendisi secer:
- **python** (tasinabilir): parcalar Python'da kosinus ile karsilastirilir.
- **pgvector**: `pgvector` uzantisi ve `vektor_parcasi.vektor_pg` kolonu varsa
  `<=>` operatoru ile SQL'de siralanir.

Secilen yol `arama_yolu()` ile bildirilir; `/rag/ara` yanitindaki `ayrinti.yol`
alanini bu fonksiyon besler. Tasinabilir yol icin belgelenen olcek siniri
200.000 parcadir; uzerinde pgvector onerilir.
"""

from __future__ import annotations

import math

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from arkauc.app.cekirdek.hatalar import Bulunamadi
from bdm_veritabani.modeller import BelgeKaynagi, VektorBelgesi, VektorParcasi

#: Parca hedef uzunlugu (karakter).
PARCA_BOYUT = 800
#: Komsu parcalar arasindaki ortusme (karakter).
ORTUSME = 120
#: Bundan kisa parca uretilmez; artan kuyruk bir onceki parcaya eklenir.
MIN_PARCA = 50
#: Dondurulmus varsayilan ust-k (bkz. ayarlar.rag_ust_k).
UST_K = 4

#: Cumle/paragraf sonu sayilan karakterler (geriye dogru ilk bulunan kesim noktasi).
_CUMLE_SONU = "\n.!?"


def _cumle_kesimi(metin: str, baslangic: int, bitis: int) -> int | None:
    """`[baslangic, bitis)` icinde cumle/paragraf sonuna en yakin kesimi bulur.

    Erken kesimi onlemek icin kesim noktasi pencerenin yarisindan sonra olmali;
    bulunamazsa `None` doner (cagiran kelime ya da sert kesim uygular).
    """
    esik = baslangic + max(MIN_PARCA, (bitis - baslangic) // 2)
    for konum in range(bitis - 1, esik - 1, -1):
        if metin[konum] in _CUMLE_SONU:
            return konum + 1
    return None


def _kelime_kesimi(metin: str, baslangic: int, bitis: int) -> int | None:
    """Bosluga denk gelen en yakin kesimi bulur (kelimeyi bolmemek icin)."""
    esik = baslangic + max(MIN_PARCA, (bitis - baslangic) // 2)
    for konum in range(bitis - 1, esik - 1, -1):
        if metin[konum].isspace():
            return konum
    return None


def parcala(metin: str, *, boyut: int = PARCA_BOYUT, ortusme: int = ORTUSME) -> list[str]:
    """Metni ~`boyut` karakterlik ortusen parcalara boler.

    Kesimler mumkunse cumle/paragraf sonuna, olmazsa kelime sinirina denk
    getirilir. `MIN_PARCA`dan kisa artan kuyruk bir onceki parcaya eklenir
    (bu durumda yalnizca son parca `boyut`u asabilir). Bos metin `[]` doner.
    """
    if boyut <= 0:
        raise ValueError("boyut pozitif olmalı")
    icerik = (metin or "").strip()
    if not icerik:
        return []
    if len(icerik) <= boyut:
        return [icerik]

    adim = max(1, min(ortusme, boyut - 1))
    parcalar: list[str] = []
    baslangic = 0
    uzunluk = len(icerik)
    while baslangic < uzunluk:
        bitis = min(baslangic + boyut, uzunluk)
        if bitis < uzunluk:
            kesim = _cumle_kesimi(icerik, baslangic, bitis)
            if kesim is None:
                kesim = _kelime_kesimi(icerik, baslangic, bitis)
            if kesim is not None:
                bitis = kesim
        parca = icerik[baslangic:bitis].strip()
        if parca:
            parcalar.append(parca)
        if bitis >= uzunluk:
            break
        # Ortusme penceresi tamamen bosluksa (paragraf sonu) pencereyi geriye kaydir;
        # boylece sonraki parca her zaman bir oncekinin iceriginden baslar.
        sonraki = max(bitis - adim, baslangic + 1)
        while sonraki > baslangic and not icerik[sonraki:bitis].strip():
            sonraki = max(baslangic + 1, sonraki - adim)
        while sonraki < uzunluk and icerik[sonraki].isspace():
            sonraki += 1
        baslangic = sonraki

    if len(parcalar) >= 2 and len(parcalar[-1]) < MIN_PARCA:
        parcalar[-2] = f"{parcalar[-2]} {parcalar[-1]}".strip()
        parcalar.pop()
    return parcalar or [icerik]


def kosinus(a: list[float], b: list[float]) -> float:
    """Iki vektor arasindaki kosinus benzerligi (-1..1).

    Sifir vektorde `ZeroDivisionError` yerine `0.0` doner. Uzunluklar farkli
    ise `ValueError` yukselir (farkli gomme modellerinin vektorleri
    karsilastirilamaz).
    """
    if len(a) != len(b):
        raise ValueError("vektor uzunluklari esit olmali")
    carpim = 0.0
    a_norm = 0.0
    b_norm = 0.0
    for x, y in zip(a, b):
        carpim += x * y
        a_norm += x * x
        b_norm += y * y
    if a_norm <= 0.0 or b_norm <= 0.0:
        return 0.0
    return carpim / math.sqrt(a_norm * b_norm)


def token_tahmini(icerik: str) -> int:
    """Kaba token tahmini (kayit amacli; tam tokenizer cagrilmaz)."""
    return max(1, len(icerik) // 4)


# -- belge/parca kaliciligi -------------------------------------------------


async def belge_getir(oturum: AsyncSession, org_id: int, belge_id: int) -> VektorBelgesi:
    """Belgeyi org kapsaminda getirir; baska org'un belgesi `404` gibi gorunur."""
    belge = (
        await oturum.execute(
            sa.select(VektorBelgesi).where(
                VektorBelgesi.id == belge_id, VektorBelgesi.org_id == org_id
            )
        )
    ).scalar_one_or_none()
    if belge is None:
        raise Bulunamadi("belge_bulunamadi", {"belge_id": belge_id})
    return belge


async def belgeleri_getir(oturum: AsyncSession, org_id: int) -> list[VektorBelgesi]:
    """Aktif organizasyonun belgeleri (en yeni once)."""
    return list(
        (
            await oturum.execute(
                sa.select(VektorBelgesi)
                .where(VektorBelgesi.org_id == org_id)
                .order_by(VektorBelgesi.id.desc())
            )
        )
        .scalars()
        .all()
    )


async def parcalari_getir(
    oturum: AsyncSession, org_id: int, belge_id: int
) -> list[VektorParcasi]:
    """Belgenin parcalari `sira` artan sirada."""
    return list(
        (
            await oturum.execute(
                sa.select(VektorParcasi)
                .where(VektorParcasi.org_id == org_id, VektorParcasi.belge_id == belge_id)
                .order_by(VektorParcasi.sira)
            )
        )
        .scalars()
        .all()
    )


async def parcalari_yaz(
    oturum: AsyncSession,
    *,
    org_id: int,
    belge_id: int,
    parcalar: list[str],
    vektorler: list[list[float]],
) -> int:
    """Parcalari ve vektorlerini yazar; belgenin eski parcalari degistirilir.

    `vektor_belgesi.parca_sayisi` yazilan parca sayisina guncellenir. Parca ve
    vektor sayilari farkli ise `ValueError` yukselir (programlama hatasi).
    """
    if len(parcalar) != len(vektorler):
        raise ValueError("parca ve vektor sayilari esit olmali")
    await oturum.execute(
        sa.delete(VektorParcasi).where(
            VektorParcasi.org_id == org_id, VektorParcasi.belge_id == belge_id
        )
    )
    for sira, (icerik, vektor) in enumerate(zip(parcalar, vektorler)):
        oturum.add(
            VektorParcasi(
                org_id=org_id,
                belge_id=belge_id,
                sira=sira,
                icerik=icerik,
                vektor=[float(deger) for deger in vektor],
                token_sayisi=token_tahmini(icerik),
            )
        )
    belge = await oturum.get(VektorBelgesi, belge_id)
    if belge is not None:
        belge.parca_sayisi = len(parcalar)
    await oturum.flush()
    return len(parcalar)


async def belge_olustur(
    oturum: AsyncSession,
    *,
    org_id: int,
    ad: str,
    kaynak: BelgeKaynagi,
    dosya_id: int | None,
    meta: dict | None,
) -> VektorBelgesi:
    """Vektor belgesi kaydi uretir (parcalar ayrica yazilir)."""
    belge = VektorBelgesi(
        org_id=org_id,
        ad=ad,
        kaynak=kaynak,
        dosya_id=dosya_id,
        belge_meta=dict(meta or {}),
        parca_sayisi=0,
    )
    oturum.add(belge)
    await oturum.flush()
    await oturum.refresh(belge)
    return belge


async def belge_sil(oturum: AsyncSession, org_id: int, belge_id: int) -> None:
    """Belgeyi ve parcalarini siler (org kapsaminda)."""
    await oturum.execute(
        sa.delete(VektorParcasi).where(
            VektorParcasi.org_id == org_id, VektorParcasi.belge_id == belge_id
        )
    )
    await oturum.execute(
        sa.delete(VektorBelgesi).where(
            VektorBelgesi.id == belge_id, VektorBelgesi.org_id == org_id
        )
    )
    await oturum.flush()


# -- arama -----------------------------------------------------------------


async def _pgvector_kullanilabilir(oturum: AsyncSession) -> bool:
    """`pgvector` uzantisi + `vektor_pg` kolonu var mi (yalniz PostgreSQL)."""
    baglanti = oturum.get_bind()
    if baglanti is None or baglanti.dialect.name != "postgresql":
        return False
    try:
        uzanti = (
            await oturum.execute(
                sa.text("SELECT 1 FROM pg_extension WHERE extname = 'pgvector'")
            )
        ).first()
        if uzanti is None:
            return False
        kolon = (
            await oturum.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'vektor_parcasi' AND column_name = 'vektor_pg'"
                )
            )
        ).first()
    except sa.exc.SQLAlchemyError:  # pragma: no cover - yalniz bozuk baglanti
        return False
    return kolon is not None


async def arama_yolu(oturum: AsyncSession) -> str:
    """Kullanilacak arama yolu: `"pgvector"` ya da `"python"`."""
    return "pgvector" if await _pgvector_kullanilabilir(oturum) else "python"


def _vektor_metni(vektor: list[float]) -> str:
    return "[" + ",".join(repr(float(deger)) for deger in vektor) + "]"


async def _pg_ara(
    oturum: AsyncSession,
    *,
    org_id: int,
    sorgu_vektoru: list[float],
    ust_k: int,
    belge_idleri: list[int] | None,
) -> list[dict]:
    kosullar = ["p.org_id = :org_id", "b.org_id = :org_id"]
    parametreler: dict[str, object] = {
        "org_id": org_id,
        "vec": _vektor_metni(sorgu_vektoru),
        "ust_k": ust_k,
    }
    if belge_idleri is not None:
        if not belge_idleri:
            return []
        kosullar.append("p.belge_id = ANY(CAST(:belge_idleri AS int[]))")
        parametreler["belge_idleri"] = "{" + ",".join(str(int(i)) for i in belge_idleri) + "}"
    sorgu = sa.text(
        "SELECT p.belge_id, b.ad AS belge_ad, p.sira, p.icerik, "
        "1 - (p.vektor_pg <=> CAST(:vec AS vector)) AS skor "
        "FROM vektor_parcasi p JOIN vektor_belgesi b ON b.id = p.belge_id "
        "WHERE " + " AND ".join(kosullar) + " "
        "ORDER BY p.vektor_pg <=> CAST(:vec AS vector), p.belge_id, p.sira "
        "LIMIT :ust_k"
    )
    satirlar = (await oturum.execute(sorgu, parametreler)).all()
    return [
        {
            "belge_id": int(satir.belge_id),
            "belge_ad": str(satir.belge_ad),
            "sira": int(satir.sira),
            "icerik": str(satir.icerik),
            "skor": float(satir.skor),
        }
        for satir in satirlar
    ]


async def _python_ara(
    oturum: AsyncSession,
    *,
    org_id: int,
    sorgu_vektoru: list[float],
    ust_k: int,
    belge_idleri: list[int] | None,
) -> list[dict]:
    if belge_idleri is not None and not belge_idleri:
        return []
    sorgu = (
        sa.select(VektorParcasi, VektorBelgesi.ad)
        .join(VektorBelgesi, VektorBelgesi.id == VektorParcasi.belge_id)
        .where(VektorParcasi.org_id == org_id, VektorBelgesi.org_id == org_id)
    )
    if belge_idleri is not None:
        sorgu = sorgu.where(VektorParcasi.belge_id.in_(list(belge_idleri)))
    kayitlar = (await oturum.execute(sorgu)).all()

    puanli: list[tuple[float, int, int, VektorParcasi, str]] = []
    for parca, belge_ad in kayitlar:
        try:
            skor = kosinus(sorgu_vektoru, list(parca.vektor or []))
        except ValueError:
            # Farkli boyutlu vektor (gömme modeli degismis olabilir): atlanir.
            continue
        puanli.append((skor, parca.belge_id, parca.sira, parca, belge_ad))
    puanli.sort(key=lambda oge: (-oge[0], oge[1], oge[2]))
    return [
        {
            "belge_id": int(parca.belge_id),
            "belge_ad": str(belge_ad),
            "sira": int(parca.sira),
            "icerik": str(parca.icerik),
            "skor": float(skor),
        }
        for skor, _belge_id, _sira, parca, belge_ad in puanli[:ust_k]
    ]


async def vektor_ara(
    oturum: AsyncSession,
    *,
    org_id: int,
    sorgu_vektoru: list[float],
    ust_k: int = UST_K,
    belge_idleri: list[int] | None = None,
) -> list[dict]:
    """En benzer parcalari dondurur (`[{belge_id, belge_ad, sira, icerik, skor}]`).

    Sonuclar kosinus skoruna gore azalan sirali ve `ust_k` ile sinirlidir.
    Arama daima `org_id` ile filtrelenir; bilinmeyen/baska org belge kimlikleri
    hata uretmez, sonuc disinda kalir.
    """
    if ust_k <= 0:
        return []
    if await _pgvector_kullanilabilir(oturum):
        return await _pg_ara(
            oturum,
            org_id=org_id,
            sorgu_vektoru=sorgu_vektoru,
            ust_k=ust_k,
            belge_idleri=belge_idleri,
        )
    return await _python_ara(
        oturum,
        org_id=org_id,
        sorgu_vektoru=sorgu_vektoru,
        ust_k=ust_k,
        belge_idleri=belge_idleri,
    )
