import csv
import io
import datetime as dt

from db.shifts import get_shifts
from utils import parse_period, shift_hours


def render_csv(period: str, custom_from: str = "", custom_to: str = "") -> bytes:
    date_from, date_to = parse_period(period, custom_from, custom_to)
    shifts = get_shifts(date_from, date_to)

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Дата", "Работник", "Приход", "Уход", "Часы", "Авто"])
    for s in shifts:
        arr = dt.datetime.fromisoformat(s["arrived_at"])
        left_str = ""
        if s["left_at"]:
            left_dt = dt.datetime.fromisoformat(s["left_at"])
            left_str = left_dt.strftime("%H:%M")
        h = shift_hours(s)
        writer.writerow([
            arr.strftime("%d.%m.%Y"),
            s["worker_name"],
            arr.strftime("%H:%M"),
            left_str,
            f"{h:.2f}" if h is not None else "",
            "авто" if s["auto_closed"] else "",
        ])

    return ("﻿" + buf.getvalue()).encode("utf-8")
