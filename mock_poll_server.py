"""Yerel test icin sahte oylama sunucusu (yalnizca 127.0.0.1).

Calistir:  python mock_poll_server.py
Ortam:     ENFORCE_LIMIT=1  -> ayni tarayici (cerez) ikinci oyu veremez
Lider aday sari (class="leader") isaretlenir.
"""
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

HOST, PORT = "127.0.0.1", int(os.getenv("PORT", "8000"))
ENFORCE_LIMIT = os.getenv("ENFORCE_LIMIT", "1") == "1"
VOTES = {"Ilhan Fakili": 0, "Mario Rossi": 3, "Anna Bianchi": 2}

PAGE = """<!doctype html><meta charset=utf-8><title>Test Poll</title>
<style>
 body{{font-family:sans-serif;max-width:420px;margin:40px auto}}
 label.option{{display:block;padding:8px;margin:4px 0;border:1px solid #ccc}}
 label.option.leader{{background:#ffe600}}
</style>
<h2>Test oylamasi</h2>
<form method=post action=/vote>
{options}
<button type=submit>VOTA ORA</button>
</form>
<p>{msg}</p>
"""


def render(msg=""):
    leader = max(VOTES, key=VOTES.get)
    opts = "\n".join(
        f'<label class="option{" leader" if n == leader else ""}">'
        f'<input type=radio name=candidate value="{n}"> {n} ({v})</label>'
        for n, v in VOTES.items()
    )
    return PAGE.format(options=opts, msg=msg).encode()


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, cookie=None):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(render())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = parse_qs(self.rfile.read(length).decode())
        name = (data.get("candidate") or [""])[0]
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        if ENFORCE_LIMIT and "voted" in cookies:
            return self._send(render("Zaten oy kullandiniz (limit devrede)."))
        if name not in VOTES:
            return self._send(render("Aday secilmedi."))
        VOTES[name] += 1
        self._send(render("Oyunuz kaydedildi."), cookie="voted=1; Path=/")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"http://{HOST}:{PORT}  (ENFORCE_LIMIT={int(ENFORCE_LIMIT)})")
    HTTPServer((HOST, PORT), Handler).serve_forever()
