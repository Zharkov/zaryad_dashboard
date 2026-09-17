import sqlite3

from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def get_all_skills(include_deleted: bool = False):
    with db_conn() as c:
        sql = "SELECT * FROM skills"
        if not include_deleted:
            sql += " WHERE deleted_at IS NULL"
        sql += " ORDER BY name"
        return list(c.execute(sql))


def add_skill(name: str, kind: str, user: str) -> tuple[bool, str, int | None]:
    name = name.strip()
    if not name:
        return False, "Название не может быть пустым", None
    if kind not in ("skill", "trait"):
        kind = "skill"
    try:
        with db_conn() as c:
            existing = c.execute("SELECT * FROM skills WHERE name = ?", (name,)).fetchone()
            if existing:
                if existing["deleted_at"] is None:
                    return False, "Такое качество уже есть", None
                c.execute("UPDATE skills SET deleted_at = NULL, kind = ? WHERE id = ?",
                          (kind, existing["id"]))
                audit(c, "restore_skill", None, {"skill_id": existing["id"], "name": name}, user)
                return True, "OK", existing["id"]
            cur = c.execute(
                "INSERT INTO skills (name, kind, deleted_at) VALUES (?, ?, NULL)", (name, kind),
            )
            audit(c, "add_skill", None, {"skill_id": cur.lastrowid, "name": name, "kind": kind}, user)
            return True, "OK", cur.lastrowid
    except sqlite3.IntegrityError as e:
        return False, f"Ошибка БД: {e}", None


def soft_delete_skill(skill_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "UPDATE skills SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now_msk().isoformat(), skill_id),
        )
        if cur.rowcount > 0:
            audit(c, "soft_delete_skill", None, {"skill_id": skill_id}, user)
            return True
    return False


def set_worker_skill(worker_id: int, skill_id: int, rating: int, note: str, user: str) -> tuple[bool, str]:
    if not (1 <= rating <= 5):
        return False, "Оценка должна быть от 1 до 5"
    with db_conn() as c:
        c.execute(
            "INSERT INTO worker_skills (worker_id, skill_id, rating, note, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (worker_id, skill_id) DO UPDATE SET "
            "rating = excluded.rating, note = excluded.note, updated_at = excluded.updated_at",
            (worker_id, skill_id, rating, note or None, now_msk().isoformat()),
        )
        audit(c, "set_worker_skill", None,
              {"worker_id": worker_id, "skill_id": skill_id, "rating": rating}, user)
    return True, "OK"


def delete_worker_skill(worker_id: int, skill_id: int, user: str) -> bool:
    with db_conn() as c:
        cur = c.execute(
            "DELETE FROM worker_skills WHERE worker_id = ? AND skill_id = ?",
            (worker_id, skill_id),
        )
        if cur.rowcount > 0:
            audit(c, "delete_worker_skill", None,
                  {"worker_id": worker_id, "skill_id": skill_id}, user)
            return True
    return False


def get_worker_skills_map(worker_ids: list) -> dict:
    if not worker_ids:
        return {}
    with db_conn() as c:
        placeholders = ",".join("?" * len(worker_ids))
        rows = c.execute(
            f"SELECT worker_id, skill_id, rating, note FROM worker_skills "
            f"WHERE worker_id IN ({placeholders})",
            worker_ids,
        ).fetchall()
    result: dict = {}
    for row in rows:
        result.setdefault(row["worker_id"], []).append(
            {"skill_id": row["skill_id"], "rating": row["rating"], "note": row["note"]}
        )
    return result
