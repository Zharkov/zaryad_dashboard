from db.conn import db_conn
from utils import now_msk


def log_login(username: str, role: str, worker_id: int | None) -> int:
    with db_conn() as c:
        cur = c.execute(
            "INSERT INTO login_log (username, role, worker_id, login_at) "
            "VALUES (?, ?, ?, ?)",
            (username, role, worker_id, now_msk().isoformat()),
        )
        return cur.lastrowid


def log_logout(log_id: int | None) -> None:
    if not log_id:
        return
    with db_conn() as c:
        c.execute(
            "UPDATE login_log SET logout_at = ? WHERE id = ? AND logout_at IS NULL",
            (now_msk().isoformat(), log_id),
        )


def get_login_log(limit: int = 200):
    with db_conn() as c:
        return c.execute(
            "SELECT * FROM login_log ORDER BY login_at DESC LIMIT ?", (limit,)
        ).fetchall()
