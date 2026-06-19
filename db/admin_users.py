from db.conn import db_conn
from utils import now_msk


def authenticate_admin(username: str, password: str) -> bool:
    with db_conn() as c:
        row = c.execute(
            "SELECT password_plain FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()
    return row is not None and row["password_plain"] == password


def get_admin_count() -> int:
    with db_conn() as c:
        return c.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]


def list_admins() -> list:
    with db_conn() as c:
        return list(c.execute(
            "SELECT id, username, created_at FROM admin_users ORDER BY username"
        ))


def add_admin(username: str, password: str) -> tuple[bool, str]:
    try:
        with db_conn() as c:
            c.execute(
                "INSERT INTO admin_users (username, password_plain, created_at) VALUES (?, ?, ?)",
                (username, password, now_msk().isoformat()),
            )
        return True, "OK"
    except Exception as e:
        return False, str(e)


def delete_admin(username: str) -> bool:
    with db_conn() as c:
        row = c.execute(
            "SELECT id FROM admin_users WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM admin_users WHERE username = ?", (username,))
    return True


def change_password(username: str, new_password: str) -> bool:
    with db_conn() as c:
        row = c.execute(
            "SELECT id FROM admin_users WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE admin_users SET password_plain = ? WHERE username = ?",
            (new_password, username),
        )
    return True


def bootstrap_from_env(users: dict) -> int:
    count = 0
    for username, password in users.items():
        ok, _ = add_admin(username, password)
        if ok:
            count += 1
    return count
