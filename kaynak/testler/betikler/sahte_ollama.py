"""Sahte Ollama sunucusu: `/api/tags` 200 döner, `/api/generate` çağrılarını loglar.

Amaç: `YerelSurucusu` gerçek bir Ollama olmadan canlı HTTP ile denenebilsin ve
`durdur` sırasında model boşaltma çağrısı yapılıp yapılmadığı kanıtlanabilsin.
"""

from __future__ import annotations

import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = pathlib.Path(__file__).resolve().parents[1] / "gecici" / "fake_ollama.log"


def _yaz(satir: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as dosya:
        dosya.write(satir + "\n")


class Isleyici(BaseHTTPRequestHandler):
    def _json(self, kod: int, govde: dict[str, object]) -> None:
        ham = json.dumps(govde).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(ham)))
        self.end_headers()
        self.wfile.write(ham)

    def do_GET(self) -> None:  # noqa: N802
        _yaz(f"GET {self.path}")
        if self.path.startswith("/api/tags"):
            self._json(200, {"models": [{"name": "llama3:latest"}, {"name": "mistral:7b"}]})
        elif self.path.startswith("/v1/models"):
            self._json(200, {"data": [{"id": "llama3", "object": "model"}]})
        else:
            self._json(404, {"hata": "yok"})

    def do_POST(self) -> None:  # noqa: N802
        uzunluk = int(self.headers.get("Content-Length") or 0)
        govde = self.rfile.read(uzunluk).decode("utf-8") if uzunluk else ""
        _yaz(f"POST {self.path} {govde}")
        if self.path.startswith("/api/generate"):
            self._json(200, {"done": True, "response": ""})
        elif self.path.startswith("/v1/chat/completions"):
            self._json(
                200,
                {
                    "id": "chatcmpl-sahte",
                    "object": "chat.completion",
                    "model": "llama3",
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": "merhaba"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                },
            )
        else:
            self._json(404, {"hata": "yok"})

    def log_message(self, *args: object) -> None:  # sessiz
        return


if __name__ == "__main__":
    LOG.write_text("", encoding="utf-8")
    ThreadingHTTPServer(("127.0.0.1", 11435), Isleyici).serve_forever()
