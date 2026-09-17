import datetime as dt

from db.conn import db_conn
from db.audit import audit
from utils import now_msk

KINDS = ("fine", "bonus")

KIND_LABELS = {"fine": "Штраф", "bonus": "Премия"}


def safe_kind(kind: str | None) -> str:
    """Любое неизвестное значение трактуем как штраф (поведение до появления премий)."""
    return kind if kind in KINDS else "fine"


def get_fines_for_worker(worker_id: int, include_deleted: bool = False,
                         kind: str | None = None) -> list:
    sql = "SELECT * FROM fines WHERE worker_id = ?"
    params: list = [worker_id]
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    if kind in KINDS:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY date DESC, id DESC"
    with db_conn() as c:
        return list(c.execute(sql, params))


def get_fine_by_id(fine_id: int):
    with db_conn() as c:
        return c.execute("SELECT * FROM fines WHERE id = ?", (fine_id,)).fetchone()


def get_ledger(date_from: dt.date, date_to: dt.date,
               kind: str | None = None, search: str = "") -> list:
    """Все выданные штрафы и премии за период, с именем работника."""
    sql = (
        "SELECT f.*, w.name AS worker_name FROM fines f "
        "JOIN workers w ON f.worker_id = w.id "
        "WHERE f.deleted_at IS NULL AND f.date >= ? AND f.date <= ?"
    )
    params: list = [date_from.isoformat(), date_to.isoformat()]
    if kind in KINDS:
        sql += " AND f.kind = ?"
        params.append(kind)
    sql += " ORDER BY f.date DESC, f.id DESC"
    with db_conn() as c:
        rows = list(c.execute(sql, params))
    search = (search or "").strip().lower()
    if search:
        rows = [r for r in rows if search in r["worker_name"].lower()]
    return rows


def ledger_totals(rows) -> tuple[float, float]:
    """(сумма штрафов, сумма премий) по списку записей."""
    fines_total = sum(r["amount"] for r in rows if safe_kind(r["kind"]) == "fine")
    bonus_total = sum(r["amount"] for r in rows if safe_kind(r["kind"]) == "bonus")
    return fines_total, bonus_total


def add_fine(worker_id: int, date_str: str, title: str, description: str,
             amount: float, user: str, kind: str = "fine") -> tuple[bool, str, int | None]:
    kind = safe_kind(kind)
    is_bonus = kind == "bonus"
    title = title.strip()
    if not title:
        return False, "Название не может быть пустым", None
    if amount <= 0:
        return False, "Сумма должна быть больше нуля", None
    description = (description or "").strip() or None
    now = now_msk().isoformat()
    with db_conn() as c:
        cur = c.execute(
            "INSERT INTO fines (worker_id, date, kind, title, description, amount, "
            "created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (worker_id, date_str, kind, title, description, amount, user, now),
        )
        audit(c, "add_bonus" if is_bonus else "add_fine", None, {
            "fine_id": cur.lastrowid, "worker_id": worker_id, "kind": kind,
            "title": title, "amount": amount, "date": date_str,
        }, user)
        return True, "OK", cur.lastrowid


def delete_fine(fine_id: int, user: str) -> bool:
    with db_conn() as c:
        row = c.execute("SELECT kind FROM fines WHERE id = ?", (fine_id,)).fetchone()
        kind = safe_kind(row["kind"]) if row else "fine"
        cur = c.execute(
            "UPDATE fines SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now_msk().isoformat(), fine_id),
        )
        if cur.rowcount > 0:
            audit(c, "delete_bonus" if kind == "bonus" else "delete_fine", None,
                  {"fine_id": fine_id, "kind": kind}, user)
            return True
    return False
