"""Curburtme 5: ayni slug iki kez ve Turkce karakterli ad -> slug uretimi."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, yaz  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])

govde = {
    "gorunen_ad": "Slug Catismasi",
    "slug": "test-model",
    "saglayici": "openai",
    "temel_url": "https://api.openai.com/v1",
    "upstream_model": "gpt-4o-mini",
    "yerel_mi": False,
}
yaz("POST /bdm slug=test-model (1. kez)", a.post("/bdm", json=govde))
yaz("POST /bdm slug=test-model (2. kez)", a.post("/bdm", json=govde))

yaz(
    "POST /bdm Turkce ad, slug yok: 'Şirket İçi Çözüm Aracı'",
    a.post(
        "/bdm",
        json={
            "gorunen_ad": "Şirket İçi Çözüm Aracı",
            "saglayici": "openai",
            "temel_url": "https://api.openai.com/v1",
            "upstream_model": "gpt-4o-mini",
            "yerel_mi": False,
        },
    ),
)
yaz(
    "POST /bdm Turkce ad, slug yok: 'ĞÜŞİÖÇ ıİğüşöç'",
    a.post(
        "/bdm",
        json={
            "gorunen_ad": "ĞÜŞİÖÇ ıİğüşöç",
            "saglayici": "openai",
            "temel_url": "https://api.openai.com/v1",
            "upstream_model": "gpt-4o-mini",
            "yerel_mi": False,
        },
    ),
)
yaz(
    "POST /bdm ayni ad (slug yok, cakismasiz uretim beklenir): 'Şirket İçi Çözüm Aracı'",
    a.post(
        "/bdm",
        json={
            "gorunen_ad": "Şirket İçi Çözüm Aracı",
            "saglayici": "openai",
            "temel_url": "https://api.openai.com/v1",
            "upstream_model": "gpt-4o-mini",
            "yerel_mi": False,
        },
    ),
)
