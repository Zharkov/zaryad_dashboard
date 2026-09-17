import re

from db.conn import db_conn
from utils import now_msk

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def get_time_presets() -> list:
    with db_conn() as c:
        return list(c.execute(
            "SELECT id, shift_type, time FROM time_presets ORDER BY shift_type, time"
        ))


def add_time_preset(shift_type: str, time_str: str) -> tuple[bool, str, int | None]:
    if shift_type not in ("day", "night"):
        return False, "Неверный тип смены", None
    if not _TIME_RE.match(time_str or ""):
        return False, "Неверный формат времени", None
    try:
        with db_conn() as c:
            cur = c.execute(
                "INSERT INTO time_presets (shift_type, time, created_at) VALUES (?, ?, ?)",
                (shift_type, time_str, now_msk().isoformat()),
            )
        return True, "OK", cur.lastrowid
    except Exception:
        return False, "Такой шаблон уже есть", None


def delete_time_preset(preset_id: int) -> bool:
    with db_conn() as c:
        row = c.execute("SELECT id FROM time_presets WHERE id = ?", (preset_id,)).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM time_presets WHERE id = ?", (preset_id,))
    return True
