import secrets
import datetime as dt
import threading
import time

from config import SESSION_TTL_DAYS
from utils import now_msk
from db.login_log import log_login, log_logout

SESSIONS: dict[str, dict] = {}
SESSIONS_LOCK = threading.Lock()


def create_session(
    user: str,
    role: str = "admin",
    worker_id: int | None = None,
) -> str:
    token = secrets.token_urlsafe(32)
    expires = now_msk() + dt.timedelta(days=SESSION_TTL_DAYS)
    log_id = log_login(user, role, worker_id)
    with SESSIONS_LOCK:
        SESSIONS[token] = {
            "user": user,
            "role": role,
            "worker_id": worker_id,
            "expires_at": expires.isoformat(),
            "log_id": log_id,
        }
    return token


def get_session(token: str) -> dict | None:
    if not token:
        return None
    expired_entry = None
    with SESSIONS_LOCK:
        s = SESSIONS.get(token)
        if not s:
            return None
        if dt.datetime.fromisoformat(s["expires_at"]) < now_msk():
            expired_entry = SESSIONS.pop(token)
        else:
            return s
    log_logout(expired_entry.get("log_id"))
    return None


def get_session_user(token: str) -> str | None:
    s = get_session(token)
    return s["user"] if s else None


def destroy_session(token: str) -> None:
    with SESSIONS_LOCK:
        s = SESSIONS.pop(token, None)
    if s:
        log_logout(s.get("log_id"))


def cleanup_sessions_loop():
    while True:
        try:
            time.sleep(3600)
            now = now_msk()
            with SESSIONS_LOCK:
                expired_tokens = [
                    t for t, s in SESSIONS.items()
                    if dt.datetime.fromisoformat(s["expires_at"]) < now
                ]
                expired = [SESSIONS.pop(t) for t in expired_tokens]
            for s in expired:
                log_logout(s.get("log_id"))
        except Exception:
            pass
