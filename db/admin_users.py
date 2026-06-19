from db.conn import db_conn
from utils import now_msk


def authenticate_admin(username: str, password: str) -> str | None:
    """Returns role ('admin' or 'accountant') if credentials match, else None."""
    with db_conn() as c:
        row = c.execute(
            "SELECT password_plain, role FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()
    if row and row["password_plain"] == password:
        return row["role"] or "admin"
    return None


def get_admin_count() -> int:
    with db_conn() as c:
        return c.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]


def list_admins() -> list:
    with db_conn() as c:
        return list(c.execute(
            "SELECT id, username, role, created_at FROM admin_users ORDER BY username"
        ))


def add_admin(username: str, password: str, role: str = "admin") -> tuple[bool, str]:
    if role not in ("admin", "accountant"):
        return False, f"Неизвестная роль: {role}"
    try:
        with db_conn() as c:
            c.execute(
                "INSERT INTO admin_users (username, password_plain, role, created_at) VALUES (?, ?, ?, ?)",
                (username, password, role, now_msk().isoformat()),
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


def change_role(username: str, new_role: str) -> bool:
    if new_role not in ("admin", "accountant"):
        return False
    with db_conn() as c:
        row = c.execute("SELECT id FROM admin_users WHERE username = ?", (username,)).fetchone()
        if not row:
            return False
        c.execute("UPDATE admin_users SET role = ? WHERE username = ?", (new_role, username))
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
