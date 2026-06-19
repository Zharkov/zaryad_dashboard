import sqlite3

from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def attach_worker_to_object(worker_id: int, object_id: int, user: str) -> bool:
    try:
        with db_conn() as c:
            c.execute(
                "INSERT INTO worker_objects (worker_id, object_id, attached_at) VALUES (?, ?, ?)",
                (worker_id, object_id, now_msk().isoformat()),
            )
            audit(c, "attach", None,
                  {"worker_id": worker_id, "object_id": object_id}, user)
            return True
    except sqlite3.IntegrityError:
        return False


def detach_worker_from_object(worker_id: int, object_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "DELETE FROM worker_objects WHERE worker_id = ? AND object_id = ?",
            (worker_id, object_id),
        )
        if cur.rowcount > 0:
            audit(c, "detach", None,
                  {"worker_id": worker_id, "object_id": object_id}, user)
            return True
    return False


def get_objects_of_worker(worker_id: int, include_deleted: bool = False):
    with db_conn() as c:
        sql = (
            "SELECT o.*, wo.attached_at FROM objects o "
            "JOIN worker_objects wo ON wo.object_id = o.id "
            "WHERE wo.worker_id = ?"
        )
        if not include_deleted:
            sql += " AND o.deleted_at IS NULL"
        sql += " ORDER BY o.name"
        return list(c.execute(sql, (worker_id,)))


def get_workers_of_object(object_id: int, include_deleted: bool = False):
    with db_conn() as c:
        sql = (
            "SELECT w.*, wo.attached_at FROM workers w "
            "JOIN worker_objects wo ON wo.worker_id = w.id "
            "WHERE wo.object_id = ?"
        )
        if not include_deleted:
            sql += " AND w.deleted_at IS NULL"
        sql += " ORDER BY w.name"
        return list(c.execute(sql, (object_id,)))


def get_worker_object_map(worker_ids: list) -> dict:
    if not worker_ids:
        return {}
    with db_conn() as c:
        placeholders = ",".join("?" * len(worker_ids))
        rows = c.execute(
            f"SELECT worker_id, object_id FROM worker_objects WHERE worker_id IN ({placeholders})",
            worker_ids,
        ).fetchall()
    result: dict = {}
    for row in rows:
        wid = row["worker_id"]
        if wid not in result:
            result[wid] = []
        result[wid].append(row["object_id"])
    return result


def count_workers_per_object():
    with db_conn() as c:
        rows = c.execute(
            "SELECT wo.object_id, COUNT(*) cnt FROM worker_objects wo "
            "JOIN workers w ON wo.worker_id = w.id "
            "WHERE w.deleted_at IS NULL GROUP BY wo.object_id"
        )
        return {r["object_id"]: r["cnt"] for r in rows}
