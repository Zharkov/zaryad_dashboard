import sqlite3

from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def get_crews(include_deleted: bool = False):
    with db_conn() as c:
        if include_deleted:
            return list(c.execute("SELECT * FROM crews ORDER BY name"))
        return list(c.execute(
            "SELECT * FROM crews WHERE deleted_at IS NULL ORDER BY name"
        ))


def get_crew_by_id(crew_id: int):
    with db_conn() as c:
        return c.execute("SELECT * FROM crews WHERE id = ?", (crew_id,)).fetchone()


def add_crew(name: str, note: str, user: str) -> tuple[bool, str, int | None]:
    name = name.strip()
    if not name:
        return False, "Название не может быть пустым", None
    note = (note or "").strip() or None
    try:
        with db_conn() as c:
            cur = c.execute(
                "INSERT INTO crews (name, note, created_at) VALUES (?, ?, ?)",
                (name, note, now_msk().isoformat()),
            )
            audit(c, "add_crew", None, {"crew_id": cur.lastrowid, "name": name}, user)
            return True, "OK", cur.lastrowid
    except sqlite3.IntegrityError as e:
        return False, str(e), None


def update_crew(crew_id: int, name: str | None, note: str | None, user: str) -> tuple[bool, str]:
    fields, params = [], []
    if name is not None:
        name = name.strip()
        if not name:
            return False, "Название не может быть пустым"
        fields.append("name = ?")
        params.append(name)
    if note is not None:
        fields.append("note = ?")
        params.append(note.strip() or None)
    if not fields:
        return False, "Нечего менять"
    params.append(crew_id)
    with db_conn() as c:
        cur = c.execute(f"UPDATE crews SET {', '.join(fields)} WHERE id = ?", params)
        if cur.rowcount == 0:
            return False, "Бригада не найдена"
        audit(c, "update_crew", None, {"crew_id": crew_id, "name": name}, user)
    return True, "OK"


def soft_delete_crew(crew_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE crews SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now_msk().isoformat(), crew_id),
        )
        if cur.rowcount > 0:
            audit(c, "soft_delete_crew", None, {"crew_id": crew_id}, user)
            return True
    return False


def add_worker_to_crew(crew_id: int, worker_id: int, user: str) -> bool:
    try:
        with db_conn() as c:
            c.execute(
                "INSERT INTO crew_workers (crew_id, worker_id, added_at) VALUES (?, ?, ?)",
                (crew_id, worker_id, now_msk().isoformat()),
            )
            audit(c, "add_crew_worker", None,
                  {"crew_id": crew_id, "worker_id": worker_id}, user)
            return True
    except sqlite3.IntegrityError:
        return False


def remove_worker_from_crew(crew_id: int, worker_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "DELETE FROM crew_workers WHERE crew_id = ? AND worker_id = ?",
            (crew_id, worker_id),
        )
        if cur.rowcount > 0:
            audit(c, "remove_crew_worker", None,
                  {"crew_id": crew_id, "worker_id": worker_id}, user)
            return True
    return False


def get_crew_workers(crew_id: int, include_deleted: bool = False):
    with db_conn() as c:
        sql = (
            "SELECT w.*, cw.added_at FROM workers w "
            "JOIN crew_workers cw ON cw.worker_id = w.id "
            "WHERE cw.crew_id = ?"
        )
        if not include_deleted:
            sql += " AND w.deleted_at IS NULL"
        sql += " ORDER BY w.name"
        return list(c.execute(sql, (crew_id,)))


def get_crews_of_worker(worker_id: int):
    with db_conn() as c:
        return list(c.execute(
            "SELECT cr.* FROM crews cr JOIN crew_workers cw ON cw.crew_id = cr.id "
            "WHERE cw.worker_id = ? AND cr.deleted_at IS NULL ORDER BY cr.name",
            (worker_id,),
        ))


def count_workers_per_crew():
    with db_conn() as c:
        rows = c.execute(
            "SELECT cw.crew_id, COUNT(*) cnt FROM crew_workers cw "
            "JOIN workers w ON cw.worker_id = w.id "
            "WHERE w.deleted_at IS NULL GROUP BY cw.crew_id"
        )
        return {r["crew_id"]: r["cnt"] for r in rows}
