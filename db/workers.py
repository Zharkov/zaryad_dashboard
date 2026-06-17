import re
import sqlite3

from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def get_workers(include_deleted: bool = False):
    with db_conn() as c:
        if include_deleted:
            return list(c.execute("SELECT * FROM workers ORDER BY name"))
        return list(c.execute(
            "SELECT * FROM workers WHERE deleted_at IS NULL ORDER BY name"
        ))


def get_worker_by_id(worker_id: int):
    with db_conn() as c:
        return c.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()


def add_worker(name: str, default_start: str, default_end: str, user: str) -> tuple[bool, str, int | None]:
    name = name.strip()
    if not name:
        return False, "Имя не может быть пустым", None
    if not re.match(r"^\d{2}:\d{2}$", default_start) or not re.match(r"^\d{2}:\d{2}$", default_end):
        return False, "График должен быть в формате HH:MM", None
    try:
        with db_conn() as c:
            existing = c.execute(
                "SELECT * FROM workers WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                if existing["deleted_at"] is None:
                    return False, "Такой работник уже есть", None
                c.execute(
                    "UPDATE workers SET deleted_at = NULL, "
                    "default_start = ?, default_end = ? WHERE id = ?",
                    (default_start, default_end, existing["id"]),
                )
                audit(c, "restore_worker", None, {
                    "worker_id": existing["id"], "name": name,
                    "default_start": default_start, "default_end": default_end,
                    "note": "via add (was soft-deleted)",
                }, user)
                return True, "OK", existing["id"]
            cur = c.execute(
                "INSERT INTO workers (name, created_at, default_start, default_end) "
                "VALUES (?, ?, ?, ?)",
                (name, now_msk().isoformat(), default_start, default_end),
            )
            audit(c, "add_worker", None, {
                "worker_id": cur.lastrowid, "name": name,
                "default_start": default_start, "default_end": default_end,
            }, user)
            return True, "OK", cur.lastrowid
    except sqlite3.IntegrityError as e:
        return False, f"Ошибка БД: {e}", None


def update_worker(worker_id: int, name: str | None = None,
                  default_start: str | None = None,
                  default_end: str | None = None,
                  user: str = "") -> tuple[bool, str]:
    fields, params = [], []
    if name is not None:
        name = name.strip()
        if not name:
            return False, "Имя не может быть пустым"
        with db_conn() as c:
            conflict = c.execute(
                "SELECT id FROM workers WHERE name = ? AND id != ?",
                (name, worker_id),
            ).fetchone()
            if conflict:
                return False, "Работник с таким именем уже есть"
        fields.append("name = ?")
        params.append(name)
    if default_start is not None:
        if not re.match(r"^\d{2}:\d{2}$", default_start):
            return False, "Приход должен быть HH:MM"
        fields.append("default_start = ?")
        params.append(default_start)
    if default_end is not None:
        if not re.match(r"^\d{2}:\d{2}$", default_end):
            return False, "Уход должен быть HH:MM"
        fields.append("default_end = ?")
        params.append(default_end)
    if not fields:
        return False, "Нечего менять"
    params.append(worker_id)
    with db_conn() as c:
        cur = c.execute(
            f"UPDATE workers SET {', '.join(fields)} WHERE id = ?", params,
        )
        if cur.rowcount == 0:
            return False, "Работник не найден"
        audit(c, "update_worker", None, {
            "worker_id": worker_id, "name": name,
            "default_start": default_start, "default_end": default_end,
        }, user)
    return True, "OK"


def soft_delete_worker(worker_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE workers SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now_msk().isoformat(), worker_id),
        )
        if cur.rowcount > 0:
            audit(c, "soft_delete_worker", None, {"worker_id": worker_id}, user)
            return True
    return False


def hard_delete_worker(worker_id: int, user: str) -> bool:
    with db_conn() as c:
        row = c.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
        audit(c, "hard_delete_worker", None,
              {"worker_id": worker_id, "name": row["name"]}, user)
    return True


def restore_worker(worker_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE workers SET deleted_at = NULL WHERE id = ?", (worker_id,),
        )
        if cur.rowcount > 0:
            audit(c, "restore_worker", None, {"worker_id": worker_id}, user)
            return True
    return False
