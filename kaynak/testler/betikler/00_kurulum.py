"""00 — Kurulum + gözlem için BDM kayıtlarının hazırlanması.

Üretir: gecici/ortam.json (jeton, bdm kimlikleri).
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
import ortak  # noqa: E402


def main() -> None:
    kayit = ortak.kurulum_yap()
    jeton = kayit["jeton"]
    print(f"kurulum tamam; yönetici id={kayit['kullanici'].get('id')}")

    idler: dict[str, int] = {}

    b = ortak.bdm_olustur("VLLM Test", "vllm", temel_url="http://localhost:8000/v1", upstream_model="mistralai/Mistral-7B-Instruct-v0.2", jeton=jeton)
    idler["vllm"] = b["id"]
    print(f"vllm bdm id={b['id']} durum={b['durum']} konteyner={b['konteyner']}")

    b = ortak.bdm_olustur("Ollama Gozlem", "ollama", temel_url="http://127.0.0.1:11435/v1", upstream_model="llama3", jeton=jeton)
    idler["ollama"] = b["id"]
    print(f"ollama bdm id={b['id']} durum={b['durum']} yerel_mi={b['yerel_mi']}")

    b = ortak.bdm_olustur("Ozel Uzak", "ozel", temel_url="http://127.0.0.1:9999/v1", upstream_model="x", jeton=jeton)
    idler["ozel"] = b["id"]
    print(f"ozel bdm id={b['id']} durum={b['durum']} yerel_mi={b['yerel_mi']}")

    b = ortak.bdm_olustur("Ollama Uzak Adres", "ollama", temel_url="http://127.0.0.1:11434/v1", upstream_model="llama3", jeton=jeton)
    idler["ollama_varsayilan"] = b["id"]
    print(f"ollama(default) bdm id={b['id']} durum={b['durum']}")

    ortak.ORTAM.write_text(json.dumps({"jeton": jeton, "bdm": idler}, indent=2), encoding="utf-8")
    print(json.dumps(idler))


if __name__ == "__main__":
    main()
