import datetime as dt
from config import TZ

LATE_THRESHOLD_MIN = 15
LATE_HARD_MIN = 60

PERIOD_LABELS = {
    "today": "Сегодня",
    "week": "Неделя",
    "first_half": "1-15",
    "second_half": "16-конец",
    "this_month": "Этот месяц",
    "prev_month": "Прошлый месяц",
    "year": "Год",
    "custom": "Произвольный",
}


def now_msk() -> dt.datetime:
    return dt.datetime.now(TZ).replace(tzinfo=None)


def hhmm_to_time(hhmm: str) -> dt.time:
    h, m = hhmm.split(":")
    return dt.time(int(h), int(m))


def shift_hours(row) -> float | None:
    if not row["left_at"]:
        return None
    arr = dt.datetime.fromisoformat(row["arrived_at"])
    left = dt.datetime.fromisoformat(row["left_at"])
    return round((left - arr).total_seconds() / 3600, 2)


def lateness(shift) -> tuple[str, str]:
    if not shift["default_start"]:
        return "", ""
    arr = dt.datetime.fromisoformat(shift["arrived_at"]).time()
    sched = hhmm_to_time(shift["default_start"])
    arr_min = arr.hour * 60 + arr.minute
    sched_min = sched.hour * 60 + sched.minute
    diff = arr_min - sched_min
    if diff < -5:
        return "early", "раньше"
    if abs(diff) <= LATE_THRESHOLD_MIN:
        return "", ""
    if diff > LATE_HARD_MIN:
        return "very-late", f"+{diff}мин"
    return "late", f"+{diff}мин"


def parse_period(period: str, custom_from: str = "", custom_to: str = "") -> tuple[dt.date, dt.date]:
    today = now_msk().date()
    if period == "custom" and custom_from and custom_to:
        try:
            f = dt.date.fromisoformat(custom_from)
            t = dt.date.fromisoformat(custom_to)
            if f > t:
                f, t = t, f
            return f, t
        except ValueError:
            pass
    if period == "this_month":
        f = today.replace(day=1)
        t = (f + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
    elif period == "prev_month":
        first = today.replace(day=1)
        t = first - dt.timedelta(days=1)
        f = t.replace(day=1)
    elif period == "first_half":
        f = today.replace(day=1)
        t = today.replace(day=15)
    elif period == "second_half":
        f = today.replace(day=16)
        nm_first = (today.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
        t = nm_first - dt.timedelta(days=1)
    elif period == "week":
        f = today - dt.timedelta(days=today.weekday())
        t = f + dt.timedelta(days=6)
    elif period == "year":
        f = today.replace(month=1, day=1)
        t = today.replace(month=12, day=31)
    elif period == "today":
        f = t = today
    else:
        f = today.replace(day=1)
        t = (f + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
    return f, t
