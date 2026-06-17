import secrets
import datetime as dt
import threading
import time

from config import SESSION_TTL_DAYS
from utils import now_msk

SESSIONS: dict[str, dict] = {}
SESSIONS_LOCK = threading.Lock()


def create_session(user: str, role: str = "admin", worker_id: int | None = None) -> str:
    token = secrets.token_urlsafe(32)
    expires = now_msk() + dt.timedelta(days=SESSION_TTL_DAYS)
    with SESSIONS_LOCK:
        SESSIONS[token] = {
            "user": user,
            "role": role,
            "worker_id": worker_id,
            "expires_at": expires.isoformat(),
        }
    return token


def get_session(token: str) -> dict | None:
    if not token:
        return None
    with SESSIONS_LOCK:
        s = SESSIONS.get(token)
        if not s:
            return None
        if dt.datetime.fromisoformat(s["expires_at"]) < now_msk():
            del SESSIONS[token]
            return None
        return s


def get_session_user(token: str) -> str | None:
    s = get_session(token)
    return s["user"] if s else None


def destroy_session(token: str) -> None:
    with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


def cleanup_sessions_loop():
    while True:
        try:
            time.sleep(3600)
            now = now_msk()
            with SESSIONS_LOCK:
                expired = [t for t, s in SESSIONS.items()
                           if dt.datetime.fromisoformat(s["expires_at"]) < now]
                for t in expired:
                    del SESSIONS[t]
        except Exception:
            pass
