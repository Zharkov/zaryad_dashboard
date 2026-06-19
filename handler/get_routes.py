import urllib.parse
from pathlib import Path

from views import (
    render_login, render_dashboard, render_workers,
    render_worker_profile, render_my_page,
    render_objects, render_object_detail, render_csv, render_xlsx,
    render_users,
)
from sessions import get_session

_STATIC_DIR = Path(__file__).parent.parent / "static"
_MIME = {".css": "text/css", ".js": "application/javascript",
         ".png": "image/png", ".svg": "image/svg+xml",
         ".ico": "image/x-icon", ".woff2": "font/woff2"}


class GetRoutesMixin:
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path.startswith("/static/"):
            filename = path[len("/static/"):]
            if not filename or "/" in filename or ".." in filename:
                self._not_found()
                return
            file_path = _STATIC_DIR / filename
            if not file_path.exists():
                self._not_found()
                return
            ctype = _MIME.get(file_path.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "max-age=3600")
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
            return

        if path == "/login":
            self._send(200, render_login())
            return

        if path == "/logout":
            cookie = self.headers.get("Cookie", "")
            token = ""
            for part in cookie.split(";"):
                kv = part.strip().split("=", 1)
                if len(kv) == 2 and kv[0].strip() == "session":
                    token = kv[1].strip()
            if token:
                from sessions import destroy_session
                destroy_session(token)
            self.send_response(303)
            self._clear_session_cookie()
            self.send_header("Location", "/login")
            self.end_headers()
            return

        user = self._session_user()
        if user is None:
            self._redirect("/login")
            return

        session_data = None
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            kv = part.strip().split("=", 1)
            if len(kv) == 2 and kv[0].strip() == "session":
                session_data = get_session(kv[1].strip())
                break

        is_worker_role = session_data and session_data.get("role") == "worker"
        is_accountant_role = bool(session_data and session_data.get("role") == "accountant")

        if path in ("/", ""):
            if is_worker_role:
                worker_id = session_data.get("worker_id")
                if not worker_id:
                    self._send(403, "<h1>403 — нет работника</h1>")
                    return
                body = render_my_page(worker_id, user)
                self._send(200, body or "<h1>404</h1>")
            else:
                period = self._qs_get("period", "week")
                search = self._qs_get("search", "")
                custom_from = self._qs_get("from", "")
                custom_to = self._qs_get("to", "")
                self._send(200, render_dashboard(period, search, user, custom_from, custom_to, is_accountant=is_accountant_role))
            return

        if path == "/my":
            if not is_worker_role:
                self._redirect("/")
                return
            worker_id = session_data.get("worker_id")
            body = render_my_page(worker_id, user) if worker_id else None
            self._send(200, body or "<h1>404</h1>")
            return

        if is_worker_role:
            self._send(403, "<h1>403 — доступ закрыт</h1>")
            return

        if path == "/api/object_comments":
            object_id = self._qs_get("object_id", "")
            if not object_id.isdigit():
                self._send_json({"error": "bad id"}, 400)
                return
            from db.comments import get_object_comments
            comments = [dict(c) for c in get_object_comments(int(object_id))]
            self._send_json({"ok": True, "comments": comments})
            return

        if path == "/api/shift_comments":
            shift_id = self._qs_get("shift_id", "")
            if not shift_id.isdigit():
                self._send_json({"error": "bad id"}, 400)
                return
            from db.comments import get_shift_comments
            comments = [dict(c) for c in get_shift_comments(int(shift_id))]
            self._send_json({"ok": True, "comments": comments})
            return

        if path == "/workers":
            search = self._qs_get("search", "")
            self._send(200, render_workers(search, user))
            return

        if path == "/worker":
            wid = self._qs_get("id", "")
            if not wid.isdigit():
                self._not_found("работник не найден")
                return
            body = render_worker_profile(int(wid), user)
            if body is None:
                self._not_found("работник не найден")
                return
            self._send(200, body)
            return

        if path == "/objects":
            search = self._qs_get("search", "")
            self._send(200, render_objects(search, user))
            return

        if path == "/object":
            oid = self._qs_get("id", "")
            if not oid.isdigit():
                self._not_found("объект не найден")
                return
            body = render_object_detail(int(oid), user)
            if body is None:
                self._not_found("объект не найден")
                return
            self._send(200, body)
            return

        if path == "/users":
            if is_accountant_role:
                self._send(403, "<h1>403 — доступ закрыт</h1>")
                return
            self._send(200, render_users(user))
            return

        if path == "/export":
            period = self._qs_get("period", "week")
            custom_from = self._qs_get("from", "")
            custom_to = self._qs_get("to", "")
            search = self._qs_get("search", "")
            data = render_csv(period, custom_from, custom_to, search)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="shifts_{period}.csv"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/export_xlsx":
            period = self._qs_get("period", "week")
            custom_from = self._qs_get("from", "")
            custom_to = self._qs_get("to", "")
            search = self._qs_get("search", "")
            data = render_xlsx(period, custom_from, custom_to, search)
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            self.send_header("Content-Disposition",
                             f'attachment; filename="shifts_{period}.xlsx"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._not_found()
