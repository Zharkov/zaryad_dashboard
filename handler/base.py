import json
import urllib.parse
from http.server import BaseHTTPRequestHandler


class BaseHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code: int, body: str | bytes, content_type: str = "text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict, code: int = 200):
        self._send(code, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8")

    def _redirect(self, location: str, code: int = 303):
        self.send_response(code)
        self.send_header("Location", location)
        self.end_headers()

    def _not_found(self, msg: str = "Not found"):
        self._send(404, f"<h1>404 — {msg}</h1>")

    def _forbidden(self):
        self._redirect("/login")

    def _read_body_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def _read_body_form(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            return urllib.parse.parse_qs(raw, keep_blank_values=True)
        except Exception:
            return {}

    def _qs(self) -> dict:
        parsed = urllib.parse.urlparse(self.path)
        return urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    def _qs_get(self, key: str, default: str = "") -> str:
        return (self._qs().get(key, [default]) or [default])[0]

    def _session_user(self) -> str | None:
        from sessions import get_session_user
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            kv = part.strip().split("=", 1)
            if len(kv) == 2 and kv[0].strip() == "session":
                return get_session_user(kv[1].strip())
        return None

    def _set_session_cookie(self, token: str):
        self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Lax")

    def _clear_session_cookie(self):
        self.send_header("Set-Cookie", "session=; Path=/; HttpOnly; Max-Age=0")
