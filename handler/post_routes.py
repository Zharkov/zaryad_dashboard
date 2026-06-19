import datetime as dt
import urllib.parse

from db.admin_users import authenticate_admin
from sessions import create_session, get_session
from db.workers import (
    add_worker, update_worker,
    soft_delete_worker, hard_delete_worker, restore_worker,
)
from db.shifts import (
    get_open_shift_for_worker, get_shift_by_id,
    create_arrival, set_departure, create_full_shift,
    update_shift, reopen_shift, delete_shift,
)
from db.objects import (
    add_object, update_object, soft_delete_object, restore_object,
)
from db.attachments import attach_worker_to_object, detach_worker_from_object
from db.credentials import (
    authenticate_worker, create_or_reset_worker_credential,
    block_worker_credential, unblock_worker_credential,
)
from utils import now_msk


class PostRoutesMixin:
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/login":
            self._handle_login()
            return

        user = self._session_user()
        if user is None:
            self._send_json({"error": "unauthorized"}, 401)
            return

        cookie = self.headers.get("Cookie", "")
        session_data = None
        for part in cookie.split(";"):
            kv = part.strip().split("=", 1)
            if len(kv) == 2 and kv[0].strip() == "session":
                session_data = get_session(kv[1].strip())
                break

        is_worker = session_data and session_data.get("role") == "worker"
        is_accountant = session_data and session_data.get("role") == "accountant"

        ADMIN_ROUTES = {
            "/api/mass_mark": self._api_mass_mark,
            "/api/backdate_shift": self._api_backdate_shift,
            "/api/edit_shift": self._api_edit_shift,
            "/api/reopen_shift": self._api_reopen_shift,
            "/api/delete_shift": self._api_delete_shift,
            "/api/close_shift_now": self._api_close_shift_now,
            "/api/add_worker": self._api_add_worker,
            "/api/update_worker": self._api_update_worker,
            "/api/soft_delete_worker": self._api_soft_delete_worker,
            "/api/hard_delete_worker": self._api_hard_delete_worker,
            "/api/restore_worker": self._api_restore_worker,
            "/api/create_worker_access": self._api_create_worker_access,
            "/api/reset_worker_access": self._api_reset_worker_access,
            "/api/block_worker_access": self._api_block_worker_access,
            "/api/unblock_worker_access": self._api_unblock_worker_access,
            "/api/add_object": self._api_add_object,
            "/api/update_object": self._api_update_object,
            "/api/delete_object": self._api_delete_object,
            "/api/restore_object": self._api_restore_object,
            "/api/set_object_workers": self._api_set_object_workers,
            "/api/set_worker_objects": self._api_set_worker_objects,
            "/api/detach_worker": self._api_detach_worker,
            "/api/add_comment": self._api_add_comment,
            "/api/delete_comment": self._api_delete_comment,
            "/api/add_shift_comment": self._api_add_shift_comment,
            "/api/delete_shift_comment": self._api_delete_shift_comment,
            "/api/add_object_comment": self._api_add_object_comment,
            "/api/delete_object_comment": self._api_delete_object_comment,
            "/api/delete_worker_access": self._api_delete_worker_access,
            "/api/set_worker_password": self._api_set_worker_password,
            "/api/add_user": self._api_add_user,
            "/api/change_user_role": self._api_change_user_role,
            "/api/change_user_password": self._api_change_user_password,
            "/api/delete_user": self._api_delete_user,
        }

        handler = ADMIN_ROUTES.get(path)
        if handler:
            if is_worker:
                self._send_json({"error": "forbidden"}, 403)
            elif is_accountant:
                self._send_json({"ok": False, "error": "Только просмотр"}, 403)
            else:
                handler(user)
        else:
            self._not_found()

    def _handle_login(self):
        body = self._read_body_form()
        username = (body.get("username", [""])[0] or "").strip()
        password = (body.get("password", [""])[0] or "").strip()

        if username and password:
            role = authenticate_admin(username, password)
            if role:
                token = create_session(username, role=role)
                self.send_response(303)
                self._set_session_cookie(token)
                self.send_header("Location", "/")
                self.end_headers()
                return

            worker_id = authenticate_worker(username, password)
            if worker_id:
                token = create_session(username, role="worker", worker_id=worker_id)
                self.send_response(303)
                self._set_session_cookie(token)
                self.send_header("Location", "/my")
                self.end_headers()
                return

        from views import render_login
        self._send(200, render_login(error="Неверный логин или пароль"))

    def _api_mass_mark(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        action = data.get("action")
        time_str = data.get("time", "")
        worker_ids = data.get("worker_ids", [])
        if action not in ("arr", "dep") or not time_str or not worker_ids:
            self._send_json({"error": "invalid params"}, 400)
            return
        now = now_msk()
        try:
            h, m = map(int, time_str.split(":"))
            mark_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        except Exception:
            self._send_json({"error": "bad time"}, 400)
            return
        ok_count = err_count = 0
        for wid in worker_ids:
            if action == "arr":
                ok, _ = create_arrival(wid, mark_dt, admin)
            else:
                ok, _ = set_departure(wid, mark_dt, admin)
            if ok:
                ok_count += 1
            else:
                err_count += 1
        self._send_json({"ok": True, "ok_count": ok_count, "err_count": err_count})

    def _api_backdate_shift(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        date_str = data.get("date", "")
        arrived_str = data.get("arrived", "")
        left_str = data.get("left", "")
        worker_ids = data.get("worker_ids", [])
        if not date_str or not arrived_str or not worker_ids:
            self._send_json({"error": "invalid params"}, 400)
            return
        try:
            d = dt.date.fromisoformat(date_str)
        except Exception:
            self._send_json({"error": "bad date"}, 400)
            return
        try:
            ah, am = map(int, arrived_str.split(":"))
            arr_dt = dt.datetime(d.year, d.month, d.day, ah, am)
        except Exception:
            self._send_json({"error": "bad arrived time"}, 400)
            return
        left_dt = None
        if left_str:
            try:
                lh, lm = map(int, left_str.split(":"))
                left_dt = dt.datetime(d.year, d.month, d.day, lh, lm)
            except Exception:
                pass
        ok_count = skip_count = 0
        errors = []
        for wid in worker_ids:
            if left_dt:
                ok, msg = create_full_shift(wid, arr_dt, left_dt, admin)
            else:
                ok, msg = create_arrival(wid, arr_dt, admin)
            if ok:
                ok_count += 1
            else:
                skip_count += 1
                errors.append(msg)
        self._send_json({"ok": True, "ok_count": ok_count, "skip_count": skip_count, "errors": errors})

    def _api_edit_shift(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        shift_id = data.get("id")
        arrived_str = data.get("arrived", "")
        left_str = data.get("left", "")
        if not shift_id:
            self._send_json({"error": "no id"}, 400)
            return
        shift = get_shift_by_id(shift_id)
        if not shift:
            self._send_json({"error": "shift not found"}, 404)
            return
        base_date = dt.datetime.fromisoformat(shift["arrived_at"]).date()
        arr_dt = None
        if arrived_str:
            try:
                ah, am = map(int, arrived_str.split(":"))
                arr_dt = dt.datetime(base_date.year, base_date.month, base_date.day, ah, am)
            except Exception:
                pass
        left_dt = None
        if left_str:
            try:
                lh, lm = map(int, left_str.split(":"))
                left_dt = dt.datetime(base_date.year, base_date.month, base_date.day, lh, lm)
            except Exception:
                pass
        ok, msg = update_shift(shift_id, arr_dt, left_dt, admin)
        if ok:
            self._send_json({"ok": True})
        else:
            self._send_json({"error": msg}, 400)

    def _api_reopen_shift(self, admin: str):
        data = self._read_body_json()
        shift_id = data.get("id") if data else None
        if not shift_id:
            self._send_json({"error": "no id"}, 400)
            return
        ok, msg = reopen_shift(shift_id, admin)
        if ok:
            self._send_json({"ok": True})
        else:
            self._send_json({"error": msg}, 400)

    def _api_delete_shift(self, admin: str):
        data = self._read_body_json()
        shift_id = data.get("id") if data else None
        if not shift_id:
            self._send_json({"error": "no id"}, 400)
            return
        if delete_shift(shift_id, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "shift not found"}, 404)

    def _api_close_shift_now(self, admin: str):
        data = self._read_body_json()
        shift_id = data.get("id") if data else None
        if not shift_id:
            self._send_json({"error": "no id"}, 400)
            return
        now = now_msk()
        ok, msg = update_shift(shift_id, None, now, admin)
        if ok:
            self._send_json({"ok": True, "time": now.strftime("%H:%M")})
        else:
            self._send_json({"error": msg}, 400)

    def _api_add_worker(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        name = (data.get("name") or "").strip()
        ds = (data.get("default_start") or "").strip()
        de = (data.get("default_end") or "").strip()
        if not name or not ds or not de:
            self._send_json({"error": "missing fields"}, 400)
            return
        ok, msg, wid = add_worker(name, ds, de, admin)
        if ok:
            self._send_json({"ok": True, "id": wid})
        else:
            self._send_json({"error": msg}, 400)

    def _api_update_worker(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        wid = data.get("id")
        name = (data.get("name") or "").strip()
        ds = (data.get("default_start") or "").strip() or None
        de = (data.get("default_end") or "").strip() or None
        if not wid or not name:
            self._send_json({"error": "missing fields"}, 400)
            return
        ok, msg = update_worker(wid, name, ds, de, admin)
        if ok:
            self._send_json({"ok": True})
        else:
            self._send_json({"error": msg}, 400)

    def _api_soft_delete_worker(self, admin: str):
        data = self._read_body_json()
        wid = data.get("id") if data else None
        if not wid:
            self._send_json({"error": "no id"}, 400)
            return
        if soft_delete_worker(wid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_hard_delete_worker(self, admin: str):
        data = self._read_body_json()
        wid = data.get("id") if data else None
        if not wid:
            self._send_json({"error": "no id"}, 400)
            return
        if hard_delete_worker(wid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_restore_worker(self, admin: str):
        data = self._read_body_json()
        wid = data.get("id") if data else None
        if not wid:
            self._send_json({"error": "no id"}, 400)
            return
        if restore_worker(wid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_create_worker_access(self, admin: str):
        data = self._read_body_json()
        wid = data.get("id") if data else None
        if not wid:
            self._send_json({"error": "no id"}, 400)
            return
        ok, msg, password = create_or_reset_worker_credential(wid, admin)
        if ok:
            self._send_json({"ok": True, "password": password})
        else:
            self._send_json({"error": msg}, 400)

    def _api_reset_worker_access(self, admin: str):
        self._api_create_worker_access(admin)

    def _api_block_worker_access(self, admin: str):
        data = self._read_body_json()
        wid = data.get("id") if data else None
        if not wid:
            self._send_json({"error": "no id"}, 400)
            return
        if block_worker_credential(wid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_unblock_worker_access(self, admin: str):
        data = self._read_body_json()
        wid = data.get("id") if data else None
        if not wid:
            self._send_json({"error": "no id"}, 400)
            return
        if unblock_worker_credential(wid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_add_object(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        name = (data.get("name") or "").strip()
        desc = (data.get("description") or "").strip()
        if not name:
            self._send_json({"error": "missing name"}, 400)
            return
        ok, msg, oid = add_object(name, desc, admin)
        if ok:
            self._send_json({"ok": True, "id": oid})
        else:
            self._send_json({"error": msg}, 400)

    def _api_update_object(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        oid = data.get("id")
        name = (data.get("name") or "").strip()
        desc = data.get("description")
        if not oid or not name:
            self._send_json({"error": "missing fields"}, 400)
            return
        ok, msg = update_object(oid, name, desc, admin)
        if ok:
            self._send_json({"ok": True})
        else:
            self._send_json({"error": msg}, 400)

    def _api_delete_object(self, admin: str):
        data = self._read_body_json()
        oid = data.get("id") if data else None
        if not oid:
            self._send_json({"error": "no id"}, 400)
            return
        if soft_delete_object(oid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_restore_object(self, admin: str):
        data = self._read_body_json()
        oid = data.get("id") if data else None
        if not oid:
            self._send_json({"error": "no id"}, 400)
            return
        if restore_object(oid, admin):
            self._send_json({"ok": True})
        else:
            self._send_json({"error": "not found"}, 404)

    def _api_set_object_workers(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        oid = data.get("object_id")
        attached = detached = 0
        for wid in data.get("attach", []):
            if attach_worker_to_object(wid, oid, admin):
                attached += 1
        for wid in data.get("detach", []):
            if detach_worker_from_object(wid, oid, admin):
                detached += 1
        self._send_json({"ok": True, "attached": attached, "detached": detached})

    def _api_set_worker_objects(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        wid = data.get("worker_id")
        attached = detached = 0
        for oid in data.get("attach", []):
            if attach_worker_to_object(wid, oid, admin):
                attached += 1
        for oid in data.get("detach", []):
            if detach_worker_from_object(wid, oid, admin):
                detached += 1
        self._send_json({"ok": True, "attached": attached, "detached": detached})

    def _api_detach_worker(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        wid = data.get("worker_id")
        oid = data.get("object_id")
        if not wid or not oid:
            self._send_json({"error": "missing params"}, 400)
            return
        detach_worker_from_object(wid, oid, admin)
        self._send_json({"ok": True})

    def _api_add_comment(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        worker_id = data.get("worker_id")
        text = (data.get("text") or "").strip()
        if not worker_id or not text:
            self._send_json({"ok": False, "error": "Нет данных"}, 400)
            return
        from db.comments import add_comment
        ok, msg, cid = add_comment(int(worker_id), admin, text)
        self._send_json({"ok": ok, "id": cid} if ok else {"ok": False, "error": msg})

    def _api_delete_comment(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        comment_id = data.get("id")
        if not comment_id:
            self._send_json({"ok": False, "error": "Нет ID"}, 400)
            return
        from db.comments import delete_comment
        ok = delete_comment(int(comment_id))
        self._send_json({"ok": ok})

    def _api_add_shift_comment(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        shift_id = data.get("shift_id")
        text = (data.get("text") or "").strip()
        if not shift_id or not text:
            self._send_json({"ok": False, "error": "Нет данных"}, 400)
            return
        from db.comments import add_shift_comment
        ok, msg, cid = add_shift_comment(int(shift_id), admin, text)
        self._send_json({"ok": ok, "id": cid} if ok else {"ok": False, "error": msg})

    def _api_delete_shift_comment(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        comment_id = data.get("id")
        if not comment_id:
            self._send_json({"ok": False, "error": "Нет ID"}, 400)
            return
        from db.comments import delete_shift_comment
        ok = delete_shift_comment(int(comment_id))
        self._send_json({"ok": ok})

    def _api_add_object_comment(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        object_id = data.get("object_id")
        text = (data.get("text") or "").strip()
        if not object_id or not text:
            self._send_json({"ok": False, "error": "Нет данных"}, 400)
            return
        from db.comments import add_object_comment
        ok, msg, cid = add_object_comment(int(object_id), admin, text)
        self._send_json({"ok": ok, "id": cid} if ok else {"ok": False, "error": msg})

    def _api_set_worker_password(self, admin: str):
        data = self._read_body_json()
        wid = data.get("worker_id") if data else None
        password = (data.get("password") or "").strip() if data else ""
        if not wid or not password:
            self._send_json({"ok": False, "error": "Нет данных"}, 400)
            return
        from db.credentials import set_worker_password
        ok = set_worker_password(int(wid), password, admin)
        self._send_json({"ok": ok} if ok else {"ok": False, "error": "Не найден"})

    def _api_delete_worker_access(self, admin: str):
        data = self._read_body_json()
        wid = data.get("worker_id") if data else None
        if not wid:
            self._send_json({"ok": False, "error": "Нет ID"}, 400)
            return
        from db.credentials import delete_worker_credential
        ok = delete_worker_credential(int(wid), admin)
        self._send_json({"ok": ok} if ok else {"ok": False, "error": "Не найден"})

    def _api_add_user(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400); return
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        role = (data.get("role") or "admin").strip()
        if not username or not password:
            self._send_json({"ok": False, "error": "Нет данных"}, 400); return
        from db.admin_users import add_admin
        ok, msg = add_admin(username, password, role)
        self._send_json({"ok": ok} if ok else {"ok": False, "error": msg})

    def _api_change_user_role(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400); return
        username = (data.get("username") or "").strip()
        role = (data.get("role") or "").strip()
        if not username or role not in ("admin", "accountant"):
            self._send_json({"ok": False, "error": "Нет данных"}, 400); return
        if username == admin:
            self._send_json({"ok": False, "error": "Нельзя изменить свою роль"}, 400); return
        from db.admin_users import change_role
        ok = change_role(username, role)
        self._send_json({"ok": ok} if ok else {"ok": False, "error": "Не найден"})

    def _api_change_user_password(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400); return
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        if not username or not password:
            self._send_json({"ok": False, "error": "Нет данных"}, 400); return
        from db.admin_users import change_password
        ok = change_password(username, password)
        self._send_json({"ok": ok} if ok else {"ok": False, "error": "Не найден"})

    def _api_delete_user(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400); return
        username = (data.get("username") or "").strip()
        if not username:
            self._send_json({"ok": False, "error": "Нет логина"}, 400); return
        if username == admin:
            self._send_json({"ok": False, "error": "Нельзя удалить себя"}, 400); return
        from db.admin_users import delete_admin
        ok = delete_admin(username)
        self._send_json({"ok": ok} if ok else {"ok": False, "error": "Не найден"})

    def _api_delete_object_comment(self, admin: str):
        data = self._read_body_json()
        if not data:
            self._send_json({"error": "bad json"}, 400)
            return
        comment_id = data.get("id")
        if not comment_id:
            self._send_json({"ok": False, "error": "Нет ID"}, 400)
            return
        from db.comments import delete_object_comment
        ok = delete_object_comment(int(comment_id))
        self._send_json({"ok": ok})
