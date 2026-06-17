import urllib.parse

from views import (
    render_login, render_dashboard, render_workers,
    render_worker_profile, render_my_page,
    render_objects, render_object_detail, render_csv,
)
from sessions import get_session


class GetRoutesMixin:
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

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
                self._send(200, render_dashboard(period, search, user, custom_from, custom_to))
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

        if path == "/export":
            period = self._qs_get("period", "week")
            custom_from = self._qs_get("from", "")
            custom_to = self._qs_get("to", "")
            data = render_csv(period, custom_from, custom_to)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="shifts_{period}.csv"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._not_found()
