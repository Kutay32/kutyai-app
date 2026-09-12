"""Yetim konusma satirlarinin kullaniciya gorunen etkisi (BLOCKER kaniti)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _ortak import istemci, jetonlari_oku, yaz  # noqa: E402

k = jetonlari_oku()
a = istemci(k["admin"])

yaz("GET /sohbet/konusmalar/2 (bdm_id=2 silinmis, yetim konusma)", a.get("/sohbet/konusmalar/2"))
yaz("GET /sohbet/konusmalar (yonetici)", a.get("/sohbet/konusmalar"))
yaz("GET /loglar/konusmalar (yonetici)", a.get("/loglar/konusmalar"))
