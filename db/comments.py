from db.conn import db_conn
from utils import now_msk


def get_comments(worker_id: int) -> list:
    with db_conn() as c:
        return list(c.execute(
            "SELECT * FROM worker_comments WHERE worker_id = ? AND deleted_at IS NULL "
            "ORDER BY created_at DESC",
            (worker_id,),
        ))


def add_comment(worker_id: int, author: str, text: str) -> tuple[bool, str, int]:
    now = now_msk().isoformat()
    with db_conn() as c:
        cur = c.execute(
            "INSERT INTO worker_comments (worker_id, author, text, created_at) VALUES (?, ?, ?, ?)",
            (worker_id, author, text, now),
        )
        return True, "OK", cur.lastrowid


def delete_comment(comment_id: int) -> bool:
    with db_conn() as c:
        row = c.execute("SELECT id FROM worker_comments WHERE id = ?", (comment_id,)).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE worker_comments SET deleted_at = ? WHERE id = ?",
            (now_msk().isoformat(), comment_id),
        )
    return True


def get_shift_comments(shift_id: int) -> list:
    with db_conn() as c:
        return list(c.execute(
            "SELECT * FROM shift_comments WHERE shift_id = ? AND deleted_at IS NULL "
            "ORDER BY created_at ASC",
            (shift_id,),
        ))


def add_shift_comment(shift_id: int, author: str, text: str) -> tuple[bool, str, int]:
    now = now_msk().isoformat()
    with db_conn() as c:
        cur = c.execute(
            "INSERT INTO shift_comments (shift_id, author, text, created_at) VALUES (?, ?, ?, ?)",
            (shift_id, author, text, now),
        )
        return True, "OK", cur.lastrowid


def delete_shift_comment(comment_id: int) -> bool:
    with db_conn() as c:
        row = c.execute("SELECT id FROM shift_comments WHERE id = ?", (comment_id,)).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE shift_comments SET deleted_at = ? WHERE id = ?",
            (now_msk().isoformat(), comment_id),
        )
    return True


def get_shift_comment_counts(shift_ids: list) -> dict:
    if not shift_ids:
        return {}
    with db_conn() as c:
        placeholders = ",".join("?" * len(shift_ids))
        rows = c.execute(
            f"SELECT shift_id, COUNT(*) as cnt FROM shift_comments "
            f"WHERE shift_id IN ({placeholders}) AND deleted_at IS NULL "
            f"GROUP BY shift_id",
            shift_ids,
        ).fetchall()
    return {row["shift_id"]: row["cnt"] for row in rows}


def get_shift_comments_bulk(shift_ids: list) -> dict:
    if not shift_ids:
        return {}
    with db_conn() as c:
        placeholders = ",".join("?" * len(shift_ids))
        rows = c.execute(
            f"SELECT * FROM shift_comments "
            f"WHERE shift_id IN ({placeholders}) AND deleted_at IS NULL "
            f"ORDER BY shift_id, created_at ASC",
            shift_ids,
        ).fetchall()
    result: dict = {}
    for row in rows:
        sid = row["shift_id"]
        if sid not in result:
            result[sid] = []
        result[sid].append(dict(row))
    return result
