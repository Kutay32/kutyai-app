"""Curburtme 8: API.md §8 ile OpenAPI karsilastirmasi (fazladan uc/parametre)."""

from __future__ import annotations

import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

sem = httpx.get("http://127.0.0.1:8102/api/openapi.json", timeout=30).json()

print("--- etiketi 'modeller' olan uclar ve parametreleri")
for yol, islemler in sorted(sem["paths"].items()):
    for yontem, islem in islemler.items():
        if "modeller" not in (islem.get("tags") or []):
            continue
        parametreler = [
            (p["name"], p["in"], p.get("required", False)) for p in islem.get("parameters", [])
        ]
        govde = "govde" if "requestBody" in islem else "-"
        print(f"{yontem.upper():6} {yol:24} params={parametreler} {govde}")

print()
print("--- API.md §8 ile beklenen kume")
print(
    json.dumps(
        [
            "GET /modeller",
            "GET /saglayicilar",
            "GET /bdm",
            "POST /bdm",
            "PATCH /bdm/{id}",
            "POST /bdm/{id}/kopyala",
            "DELETE /bdm/{id}",
        ],
        indent=2,
    )
)
