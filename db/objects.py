import sqlite3

from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def get_objects(include_deleted: bool = False):
    with db_conn() as c:
        if include_deleted:
            return list(c.execute("SELECT * FROM objects ORDER BY name"))
        return list(c.execute(
            "SELECT * FROM objects WHERE deleted_at IS NULL ORDER BY name"
        ))


def get_object_by_id(object_id: int):
    with db_conn() as c:
        return c.execute("SELECT * FROM objects WHERE id = ?", (object_id,)).fetchone()


def add_object(name: str, description: str, user: str) -> tuple[bool, str, int | None]:
    name = name.strip()
    if not name:
        return False, "Название не может быть пустым", None
    description = (description or "").strip() or None
    try:
        with db_conn() as c:
            existing = c.execute(
                "SELECT * FROM objects WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                if existing["deleted_at"] is None:
                    return False, "Объект с таким названием уже есть", None
                c.execute(
                    "UPDATE objects SET deleted_at = NULL, description = ? WHERE id = ?",
                    (description, existing["id"]),
                )
                audit(c, "restore_object", None,
                      {"object_id": existing["id"], "name": name}, user)
                return True, "OK", existing["id"]
            cur = c.execute(
                "INSERT INTO objects (name, description, created_at) VALUES (?, ?, ?)",
                (name, description, now_msk().isoformat()),
            )
            audit(c, "add_object", None,
                  {"object_id": cur.lastrowid, "name": name}, user)
            return True, "OK", cur.lastrowid
    except sqlite3.IntegrityError as e:
        return False, str(e), None


def update_object(object_id: int, name: str | None,
                  description: str | None, user: str) -> tuple[bool, str]:
    fields, params = [], []
    if name is not None:
        name = name.strip()
        if not name:
            return False, "Название не может быть пустым"
        with db_conn() as c:
            conflict = c.execute(
                "SELECT id FROM objects WHERE name = ? AND id != ?",
                (name, object_id),
            ).fetchone()
            if conflict:
                return False, "Объект с таким названием уже есть"
        fields.append("name = ?")
        params.append(name)
    if description is not None:
        desc = description.strip() or None
        fields.append("description = ?")
        params.append(desc)
    if not fields:
        return False, "Нечего менять"
    params.append(object_id)
    with db_conn() as c:
        cur = c.execute(
            f"UPDATE objects SET {', '.join(fields)} WHERE id = ?", params,
        )
        if cur.rowcount == 0:
            return False, "Объект не найден"
        audit(c, "update_object", None,
              {"object_id": object_id, "name": name, "description": description}, user)
    return True, "OK"


def soft_delete_object(object_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE objects SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now_msk().isoformat(), object_id),
        )
        if cur.rowcount > 0:
            audit(c, "soft_delete_object", None, {"object_id": object_id}, user)
            return True
    return False


def restore_object(object_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE objects SET deleted_at = NULL WHERE id = ?", (object_id,),
        )
        if cur.rowcount > 0:
            audit(c, "restore_object", None, {"object_id": object_id}, user)
            return True
    return False
