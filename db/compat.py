from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def set_compat(from_worker_id: int, to_worker_id: int, score: int, note: str, user: str) -> tuple[bool, str]:
    if from_worker_id == to_worker_id:
        return False, "Нельзя оценить совместимость с самим собой"
    if not (-2 <= score <= 2):
        return False, "Оценка должна быть от -2 до 2"
    with db_conn() as c:
        c.execute(
            "INSERT INTO worker_compat (from_worker_id, to_worker_id, score, note, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (from_worker_id, to_worker_id) DO UPDATE SET "
            "score = excluded.score, note = excluded.note, updated_at = excluded.updated_at",
            (from_worker_id, to_worker_id, score, note or None, now_msk().isoformat()),
        )
        audit(c, "set_compat", None,
              {"from_worker_id": from_worker_id, "to_worker_id": to_worker_id, "score": score}, user)
    return True, "OK"


def get_compat_matrix(worker_ids: list) -> dict:
    if not worker_ids:
        return {}
    with db_conn() as c:
        placeholders = ",".join("?" * len(worker_ids))
        rows = c.execute(
            f"SELECT from_worker_id, to_worker_id, score, note FROM worker_compat "
            f"WHERE from_worker_id IN ({placeholders}) AND to_worker_id IN ({placeholders})",
            worker_ids + worker_ids,
        ).fetchall()
    return {(r["from_worker_id"], r["to_worker_id"]): (r["score"], r["note"]) for r in rows}


def get_worker_compat_pairs(worker_id: int):
    with db_conn() as c:
        out = c.execute(
            "SELECT wc.to_worker_id AS other_id, w.name AS other_name, wc.score, wc.note, 'out' AS dir "
            "FROM worker_compat wc JOIN workers w ON w.id = wc.to_worker_id "
            "WHERE wc.from_worker_id = ? AND w.deleted_at IS NULL",
            (worker_id,),
        ).fetchall()
        inc = c.execute(
            "SELECT wc.from_worker_id AS other_id, w.name AS other_name, wc.score, wc.note, 'in' AS dir "
            "FROM worker_compat wc JOIN workers w ON w.id = wc.from_worker_id "
            "WHERE wc.to_worker_id = ? AND w.deleted_at IS NULL",
            (worker_id,),
        ).fetchall()
    return list(out) + list(inc)
