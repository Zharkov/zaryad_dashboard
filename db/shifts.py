import sqlite3
import datetime as dt

from db.conn import db_conn
from db.audit import audit
from utils import now_msk


def get_shifts(date_from: dt.date, date_to: dt.date, worker_id: int | None = None):
    with db_conn() as c:
        if worker_id is not None:
            return list(c.execute(
                "SELECT s.*, w.name as worker_name, w.default_start, w.default_end "
                "FROM shifts s JOIN workers w ON s.worker_id = w.id "
                "WHERE s.date >= ? AND s.date <= ? AND s.worker_id = ? "
                "ORDER BY s.date DESC, w.name",
                (date_from.isoformat(), date_to.isoformat(), worker_id),
            ))
        return list(c.execute(
            "SELECT s.*, w.name as worker_name, w.default_start, w.default_end "
            "FROM shifts s JOIN workers w ON s.worker_id = w.id "
            "WHERE s.date >= ? AND s.date <= ? "
            "ORDER BY s.date DESC, w.name",
            (date_from.isoformat(), date_to.isoformat()),
        ))


def get_open_shifts():
    with db_conn() as c:
        return list(c.execute(
            "SELECT s.*, w.name as worker_name "
            "FROM shifts s JOIN workers w ON s.worker_id = w.id "
            "WHERE s.left_at IS NULL ORDER BY s.arrived_at"
        ))


def get_all_shifts_for_worker(worker_id: int):
    with db_conn() as c:
        return list(c.execute(
            "SELECT s.*, w.default_start, w.default_end "
            "FROM shifts s JOIN workers w ON s.worker_id = w.id "
            "WHERE s.worker_id = ? ORDER BY s.date DESC",
            (worker_id,),
        ))


def create_arrival(worker_id: int, when: dt.datetime, user: str) -> tuple[bool, str]:
    date = when.date().isoformat()
    with db_conn() as c:
        existing = c.execute(
            "SELECT * FROM shifts WHERE worker_id = ? AND date = ?",
            (worker_id, date),
        ).fetchone()
        if existing:
            ar = dt.datetime.fromisoformat(existing["arrived_at"])
            return False, f"уже отмечен приход в {ar.strftime('%H:%M')}"
        try:
            cur = c.execute(
                "INSERT INTO shifts (worker_id, date, arrived_at) VALUES (?, ?, ?)",
                (worker_id, date, when.isoformat()),
            )
            audit(c, "create_arrival", cur.lastrowid,
                  {"worker_id": worker_id, "arrived_at": when.isoformat()}, user)
            return True, "OK"
        except sqlite3.IntegrityError as e:
            return False, str(e)


def create_full_shift(worker_id: int, arr_dt: dt.datetime,
                      left_dt: dt.datetime | None, user: str) -> tuple[bool, str]:
    if left_dt and left_dt <= arr_dt:
        return False, "уход не позже прихода"
    date_str = arr_dt.date().isoformat()
    with db_conn() as c:
        if c.execute(
            "SELECT id FROM shifts WHERE worker_id = ? AND date = ?",
            (worker_id, date_str),
        ).fetchone():
            return False, "уже есть запись за этот день"
        cur = c.execute(
            "INSERT INTO shifts (worker_id, date, arrived_at, left_at) VALUES (?, ?, ?, ?)",
            (worker_id, date_str, arr_dt.isoformat(),
             left_dt.isoformat() if left_dt else None),
        )
        audit(c, "backdate_shift", cur.lastrowid, {
            "worker_id": worker_id, "date": date_str,
            "arrived_at": arr_dt.isoformat(),
            "left_at": left_dt.isoformat() if left_dt else None,
        }, user)
    return True, "OK"


def set_departure(worker_id: int, when: dt.datetime, user: str) -> tuple[bool, str]:
    with db_conn() as c:
        row = c.execute(
            "SELECT * FROM shifts WHERE worker_id = ? AND left_at IS NULL "
            "ORDER BY arrived_at DESC LIMIT 1",
            (worker_id,),
        ).fetchone()
        if not row:
            return False, "нет открытой смены"
        if dt.datetime.fromisoformat(row["arrived_at"]) > when:
            return False, "уход раньше прихода"
        c.execute(
            "UPDATE shifts SET left_at = ?, auto_closed = 0 WHERE id = ?",
            (when.isoformat(), row["id"]),
        )
        audit(c, "set_departure", row["id"], {"left_at": when.isoformat()}, user)
    return True, "OK"


def update_shift(shift_id: int, arrived_at: dt.datetime | None,
                 left_at: dt.datetime | None, user: str) -> tuple[bool, str]:
    with db_conn() as c:
        row = c.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not row:
            return False, "Смена не найдена"
        fields, params = [], []
        if arrived_at is not None:
            fields.append("arrived_at = ?")
            params.append(arrived_at.isoformat())
        if left_at is not None:
            fields.append("left_at = ?")
            params.append(left_at.isoformat())
            fields.append("auto_closed = 0")
        if not fields:
            return False, "Нечего менять"
        params.append(shift_id)
        c.execute(f"UPDATE shifts SET {', '.join(fields)} WHERE id = ?", params)
        audit(c, "edit_shift", shift_id,
              {"arrived_at": str(arrived_at), "left_at": str(left_at)}, user)
    return True, "OK"


def reopen_shift(shift_id: int, user: str) -> tuple[bool, str]:
    with db_conn() as c:
        row = c.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not row:
            return False, "Смена не найдена"
        if not row["left_at"]:
            return False, "Смена уже открыта"
        other_open = c.execute(
            "SELECT id FROM shifts WHERE worker_id = ? AND left_at IS NULL AND id != ?",
            (row["worker_id"], shift_id),
        ).fetchone()
        if other_open:
            return False, "У работника уже есть другая открытая смена"
        c.execute(
            "UPDATE shifts SET left_at = NULL, auto_closed = 0 WHERE id = ?", (shift_id,),
        )
        audit(c, "reopen_shift", shift_id, {"prev_left_at": row["left_at"]}, user)
    return True, "OK"


def delete_shift(shift_id: int, user: str) -> bool:
    with db_conn() as c:
        row = c.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
        audit(c, "delete_shift", shift_id,
              {"worker_id": row["worker_id"], "date": row["date"]}, user)
    return True


def get_shift_by_id(shift_id: int):
    with db_conn() as c:
        return c.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()


def get_open_shift_for_worker(worker_id: int):
    with db_conn() as c:
        return c.execute(
            "SELECT * FROM shifts WHERE worker_id = ? AND left_at IS NULL "
            "ORDER BY arrived_at DESC LIMIT 1",
            (worker_id,),
        ).fetchone()
