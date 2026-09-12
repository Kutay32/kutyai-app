"""Canli backend (8103) uzerinde `POST /{id}/cek` hata yolu gozlemi.

Ollama saglayicili, adresi KAPALI olan bir BDM icin SSE akisinin nasil
bittigini ham olarak gosterir.

Calistirma:
  ./.venv/Scripts/python.exe kaynak/testler/betikler/hazirlama_cek_hata.py
"""

from __future__ import annotations

import httpx

TABAN = "http://127.0.0.1:8103/api/v1"
KAPALI = "http://127.0.0.1:8198/v1"

istemci = httpx.Client(base_url=TABAN, timeout=30.0)

giris = istemci.post(
    "/kimlik/panel-giris",
    json={"eposta": "goz-yp@gozlem.example.com", "parola": "GozlemParola1!"},
)
print("giris:", giris.status_code)
jeton = giris.json()["erisim_jetonu"]
Y = {"Authorization": f"Bearer {jeton}"}

olustur = istemci.post(
    "/bdm",
    headers=Y,
    json={"ad": "Kapali Ollama 2", "gorunen_ad": "Kapali Ollama 2", "slug": "goz-kapali-cek",
          "saglayici": "ollama", "temel_url": KAPALI, "upstream_model": "sahte-model-kucuk"},
)
print("olustur:", olustur.status_code, olustur.json()["id"])
bdm_id = olustur.json()["id"]

try:
    yanit = istemci.post(f"/bdm/hazirlama/{bdm_id}/cek", headers=Y)
    print(f"HTTP {yanit.status_code} {yanit.headers.get('content-type', '')}")
    print("govde uzunlugu:", len(yanit.content))
    print("ham govde:", repr(yanit.text))
except Exception as hata:
    print(f"ISTEMCI ISTISNASI: {type(hata).__name__}: {hata}")
