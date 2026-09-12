"""Alembic goc testleri (spec §2.4).

`alembic upgrade head` gercek bir SQLite dosyasinda kosar; sema ve varsayilan
organizasyon dogrulanir. Ikinci kosum hicbir sey degistirmemelidir (idempotent).
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
PYTHON = KOK / ".venv" / "Scripts" / "python.exe"
BEKLENEN_TABLOLAR = {
    "organizasyon",
    "uyelik",
    "plan",
    "abonelik",
    "fatura",
    "dosya",
    "vektor_belgesi",
    "vektor_parcasi",
    "arac",
    "arac_cagrisi",
    "sso_saglayici",
    "sso_kimlik",
    "posta_sablonu",
    "bdm",
    "kullanici",
}


def _alembic_calistir(db_yolu: Path) -> subprocess.CompletedProcess[str]:
    ortam = dict(os.environ)
    ortam["KUTYAI_VERITABANI_URL"] = f"sqlite+aiosqlite:///{db_yolu.as_posix()}"
    ortam["KUTYAI_GIZLI_ANAHTAR"] = "goc-test-anahtari"
    ortam["KUTYAI_SIFRELEME_ANAHTARI"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    return subprocess.run(
        [str(PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=str(KOK),
        env=ortam,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.skipif(not PYTHON.exists(), reason="Sanal ortam python bulunamadı")
def test_alembic_gocu_semayi_ve_varsayilan_organizasyonu_olusturur(tmp_path):
    db = tmp_path / "goc.db"

    ilk = _alembic_calistir(db)
    assert ilk.returncode == 0, ilk.stderr[-2000:]

    baglanti = sqlite3.connect(db)
    try:
        tablolar = {
            satir[0]
            for satir in baglanti.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert BEKLENEN_TABLOLAR <= tablolar

        organizasyonlar = baglanti.execute(
            "SELECT slug, durum FROM organizasyon"
        ).fetchall()
        assert ("varsayilan", "aktif") in organizasyonlar

        # Plan/sablon tohumu uygulama acilisinda (`tohumla`) eklenir, goc sirasinda degil.
        plan_sayisi = baglanti.execute("SELECT COUNT(*) FROM plan").fetchone()[0]
        assert plan_sayisi == 0

        kolonlar = {
            satir[1] for satir in baglanti.execute("PRAGMA table_info(bdm)")
        }
        assert "org_id" in kolonlar

        # org_id zorunlu (NOT NULL) olmali: notnull bayragi 1
        org_kolonu = [
            satir
            for satir in baglanti.execute("PRAGMA table_info(bdm)")
            if satir[1] == "org_id"
        ][0]
        assert org_kolonu[3] == 1
    finally:
        baglanti.close()

    # Ikinci kosum hicbir sey degistirmemeli (idempotent)
    ikinci = _alembic_calistir(db)
    assert ikinci.returncode == 0, ikinci.stderr[-2000:]

    baglanti = sqlite3.connect(db)
    try:
        tek = baglanti.execute(
            "SELECT COUNT(*) FROM organizasyon WHERE slug='varsayilan'"
        ).fetchone()[0]
        assert tek == 1
    finally:
        baglanti.close()


@pytest.mark.skipif(not PYTHON.exists(), reason="Sanal ortam python bulunamadı")
def test_alembic_geri_ve_ileri_gider(tmp_path):
    """downgrade -1 sonrasi upgrade head semayi geri getirir."""
    db = tmp_path / "goc2.db"
    assert _alembic_calistir(db).returncode == 0

    ortam = dict(os.environ)
    ortam["KUTYAI_VERITABANI_URL"] = f"sqlite+aiosqlite:///{db.as_posix()}"
    ortam["KUTYAI_GIZLI_ANAHTAR"] = "goc-test-anahtari"
    ortam["KUTYAI_SIFRELEME_ANAHTARI"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

    geri = subprocess.run(
        [str(PYTHON), "-m", "alembic", "downgrade", "-1"],
        cwd=str(KOK),
        env=ortam,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert geri.returncode == 0, geri.stderr[-2000:]

    baglanti = sqlite3.connect(db)
    try:
        tablolar = {
            satir[0]
            for satir in baglanti.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "organizasyon" not in tablolar
        assert "bdm" in tablolar
        kolonlar = {satir[1] for satir in baglanti.execute("PRAGMA table_info(bdm)")}
        assert "org_id" not in kolonlar
    finally:
        baglanti.close()

    assert _alembic_calistir(db).returncode == 0

    baglanti = sqlite3.connect(db)
    try:
        tablolar = {
            satir[0]
            for satir in baglanti.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "organizasyon" in tablolar
    finally:
        baglanti.close()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
