import secrets
import sqlite3

from db.conn import db_conn
from db.audit import audit
from db.workers import get_worker_by_id
from utils import now_msk


def _gen_password(length: int = 8) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_worker_credential(worker_id: int):
    with db_conn() as c:
        return c.execute(
            "SELECT * FROM worker_credentials WHERE worker_id = ?", (worker_id,)
        ).fetchone()


def create_or_reset_worker_credential(worker_id: int, user: str) -> tuple[bool, str, str | None]:
    w = get_worker_by_id(worker_id)
    if not w:
        return False, "Работник не найден", None
    if w["deleted_at"]:
        return False, "Работник удалён, восстанови его сначала", None
    new_pw = _gen_password()
    now = now_msk().isoformat()
    with db_conn() as c:
        existing = c.execute(
            "SELECT * FROM worker_credentials WHERE worker_id = ?", (worker_id,)
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE worker_credentials SET password_plain = ?, "
                "blocked = 0, updated_at = ? WHERE worker_id = ?",
                (new_pw, now, worker_id),
            )
            audit(c, "reset_worker_password", None, {"worker_id": worker_id}, user)
        else:
            c.execute(
                "INSERT INTO worker_credentials "
                "(worker_id, password_plain, blocked, created_at, updated_at) "
                "VALUES (?, ?, 0, ?, ?)",
                (worker_id, new_pw, now, now),
            )
            audit(c, "create_worker_credential", None, {"worker_id": worker_id}, user)
    return True, "OK", new_pw


def block_worker_credential(worker_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE worker_credentials SET blocked = 1, updated_at = ? WHERE worker_id = ?",
            (now_msk().isoformat(), worker_id),
        )
        if cur.rowcount > 0:
            audit(c, "block_worker_credential", None, {"worker_id": worker_id}, user)
            return True
    return False


def unblock_worker_credential(worker_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE worker_credentials SET blocked = 0, updated_at = ? WHERE worker_id = ?",
            (now_msk().isoformat(), worker_id),
        )
        if cur.rowcount > 0:
            audit(c, "unblock_worker_credential", None, {"worker_id": worker_id}, user)
            return True
    return False


def delete_worker_credential(worker_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "DELETE FROM worker_credentials WHERE worker_id = ?", (worker_id,)
        )
        if cur.rowcount > 0:
            audit(c, "delete_worker_credential", None, {"worker_id": worker_id}, user)
            return True
    return False


def authenticate_worker(login: str, password: str) -> int | None:
    if not login.isdigit():
        return None
    worker_id = int(login)
    cred = get_worker_credential(worker_id)
    if not cred:
        return None
    if cred["blocked"]:
        return None
    if not secrets.compare_digest(cred["password_plain"], password):
        return None
    w = get_worker_by_id(worker_id)
    if not w or w["deleted_at"]:
        return None
    return worker_id


def get_all_worker_credentials() -> dict[int, dict]:
    with db_conn() as c:
        out = {}
        for r in c.execute("SELECT * FROM worker_credentials"):
            out[r["worker_id"]] = {
                "password": r["password_plain"],
                "blocked": bool(r["blocked"]),
                "updated_at": r["updated_at"],
            }
        return out
