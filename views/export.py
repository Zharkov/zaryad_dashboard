import csv
import io
import datetime as dt

from db.shifts import get_shifts
from db.fines import get_ledger, safe_kind
from db.comments import get_fine_comments_bulk
from utils import parse_period, shift_hours, lateness, hhmm_to_time, PERIOD_LABELS


def _dec(value: float) -> str:
    """Float → строка с запятой как разделителем (русский Excel)."""
    return f"{value:.2f}".replace(".", ",")


def _csv_safe(value: str) -> str:
    """Экранирует ведущий =+-@, чтобы Excel/Sheets не воспринял значение как формулу."""
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _blank_stat(name: str, schedule: str) -> dict:
    return {
        "name": _csv_safe(name),
        "schedule": schedule,
        "shifts": 0,
        "hours": 0.0,
        "day_hours": 0.0,
        "night_hours": 0.0,
        "late": 0,
        "overtime": 0,
        "open": 0,
        "fines": 0.0,
        "bonuses": 0.0,
    }


def _build_stats(shifts: list, ledger: list | None = None) -> dict[int, dict]:
    stats: dict[int, dict] = {}
    for s in shifts:
        wid = s["worker_id"]
        if wid not in stats:
            stats[wid] = _blank_stat(
                s["worker_name"],
                f"{s['default_start'] or '?'}–{s['default_end'] or '?'}",
            )
        st = stats[wid]
        st["shifts"] += 1
        h = shift_hours(s)
        if h is not None:
            st["hours"] += h
            if s["shift_type"] == "night":
                st["night_hours"] += h
            else:
                st["day_hours"] += h
        else:
            st["open"] += 1

        late_cls, _ = lateness(s)
        if late_cls in ("late", "very-late"):
            st["late"] += 1

        if s["left_at"] and s["default_end"] and s["shift_type"] != "night":
            d = dt.date.fromisoformat(s["date"])
            left = dt.datetime.fromisoformat(s["left_at"])
            sched_dt = dt.datetime.combine(d, hhmm_to_time(s["default_end"]))
            if (left - sched_dt).total_seconds() > 30 * 60:
                st["overtime"] += 1

    # Штрафы и премии — в том числе для тех, у кого за период не было смен
    for row in (ledger or []):
        wid = row["worker_id"]
        if wid not in stats:
            stats[wid] = _blank_stat(row["worker_name"], "—")
        key = "bonuses" if safe_kind(row["kind"]) == "bonus" else "fines"
        stats[wid][key] += row["amount"]
    return stats


def _ledger_comments(row, comments_map: dict) -> str:
    """Комментарии к штрафу/премии одной строкой."""
    return " | ".join(
        f'{c["author"]} ({dt.datetime.fromisoformat(c["created_at"]).strftime("%d.%m.%Y %H:%M")}): '
        f'{c["text"]}'
        for c in comments_map.get(row["id"], [])
    )


def _load_ledger(date_from: dt.date, date_to: dt.date, search: str = "") -> tuple[list, dict]:
    rows = get_ledger(date_from, date_to, None, search)
    return rows, get_fine_comments_bulk([r["id"] for r in rows])


_LEDGER_HEADERS = [
    "Дата", "Работник", "Тип", "Название", "Сумма, ₽",
    "Кто выдал", "Когда выдал", "Описание", "Комментарии",
]


def render_csv(period: str, custom_from: str = "", custom_to: str = "",
               search: str = "") -> bytes:
    date_from, date_to = parse_period(period, custom_from, custom_to)
    shifts = get_shifts(date_from, date_to)
    if search:
        search_low = search.lower().strip()
        shifts = [s for s in shifts if search_low in s["worker_name"].lower()]

    # ── Сводка по работникам ─────────────────────────────────────────────────
    ledger, ledger_comments = _load_ledger(date_from, date_to, search)
    stats = _build_stats(shifts, ledger)

    # ── Формируем CSV ────────────────────────────────────────────────────────
    buf = io.StringIO()
    wr = csv.writer(buf, delimiter=";")

    period_label = PERIOD_LABELS.get(period, period)
    df_str = date_from.strftime("%d.%m.%Y")
    dt_str = date_to.strftime("%d.%m.%Y")

    # Заголовок файла
    wr.writerow(["ЗАРЯД · Табель учёта рабочего времени"])
    wr.writerow(["Период:", f"{period_label}  {df_str} — {dt_str}"])
    if search:
        wr.writerow(["Фильтр:", _csv_safe(search)])
    wr.writerow([])

    # ── Раздел 1: сводка ─────────────────────────────────────────────────────
    wr.writerow(["СВОДКА ПО РАБОТНИКАМ"])
    wr.writerow([
        "ФИО", "График", "Смен", "Дневная смена", "Ночная смена", "Общее время",
        "Среднее в день", "Опозданий", "Переработок", "Незакр. смен",
        "Штрафы, ₽", "Премии, ₽",
    ])

    total_shifts = 0
    total_hours = 0.0
    total_day_hours = 0.0
    total_night_hours = 0.0
    total_fines = 0.0
    total_bonuses = 0.0

    for st in sorted(stats.values(), key=lambda x: x["name"]):
        closed = st["shifts"] - st["open"]
        avg = round(st["hours"] / closed, 2) if closed > 0 else 0.0
        wr.writerow([
            st["name"],
            st["schedule"],
            st["shifts"],
            _dec(st["day_hours"]),
            _dec(st["night_hours"]),
            _dec(st["hours"]),
            _dec(avg),
            st["late"] or "",
            st["overtime"] or "",
            st["open"] or "",
            _dec(st["fines"]) if st["fines"] else "",
            _dec(st["bonuses"]) if st["bonuses"] else "",
        ])
        total_shifts += st["shifts"]
        total_hours += st["hours"]
        total_day_hours += st["day_hours"]
        total_night_hours += st["night_hours"]
        total_fines += st["fines"]
        total_bonuses += st["bonuses"]

    # Итоговая строка
    wr.writerow([
        "ИТОГО", "",
        total_shifts,
        _dec(total_day_hours),
        _dec(total_night_hours),
        _dec(total_hours),
        "", "", "", "",
        _dec(total_fines),
        _dec(total_bonuses),
    ])
    wr.writerow([])

    # ── Раздел 2: детализация по сменам ──────────────────────────────────────
    wr.writerow(["ДЕТАЛИЗАЦИЯ ПО СМЕНАМ"])
    wr.writerow([
        "Дата", "Работник", "График",
        "Приход", "Уход", "Часов",
        "Опоздание", "Статус", "Смена",
    ])

    for s in sorted(shifts, key=lambda x: (x["worker_name"], x["date"])):
        arr = dt.datetime.fromisoformat(s["arrived_at"])
        left_str = ""
        if s["left_at"]:
            left_str = dt.datetime.fromisoformat(s["left_at"]).strftime("%H:%M")
        h = shift_hours(s)
        late_cls, late_lbl = lateness(s)
        if not s["left_at"]:
            status = "открыта"
        elif s["auto_closed"]:
            status = "авто"
        else:
            status = ""
        wr.writerow([
            arr.strftime("%d.%m.%Y"),
            _csv_safe(s["worker_name"]),
            f"{s['default_start'] or '?'}–{s['default_end'] or '?'}",
            arr.strftime("%H:%M"),
            left_str,
            _dec(h) if h is not None else "",
            late_lbl if late_cls else "",
            status,
            "Ночная" if s["shift_type"] == "night" else "Дневная",
        ])

    # ── Раздел 3: штрафы и премии ────────────────────────────────────────────
    wr.writerow([])
    wr.writerow(["ШТРАФЫ И ПРЕМИИ"])
    wr.writerow(_LEDGER_HEADERS)

    if ledger:
        for row in ledger:
            is_bonus = safe_kind(row["kind"]) == "bonus"
            issued = dt.datetime.fromisoformat(row["created_at"])
            wr.writerow([
                dt.date.fromisoformat(row["date"]).strftime("%d.%m.%Y"),
                _csv_safe(row["worker_name"]),
                "Премия" if is_bonus else "Штраф",
                _csv_safe(row["title"]),
                _dec(row["amount"]),
                _csv_safe(row["created_by"]),
                issued.strftime("%d.%m.%Y %H:%M"),
                _csv_safe(row["description"] or ""),
                _csv_safe(_ledger_comments(row, ledger_comments)),
            ])
        wr.writerow(["ИТОГО", "", "Штрафы", "", _dec(total_fines), "", "", "", ""])
        wr.writerow(["", "", "Премии", "", _dec(total_bonuses), "", "", "", ""])
    else:
        wr.writerow(["За период штрафов и премий не выдавали"])

    return ("﻿" + buf.getvalue()).encode("utf-8")


def render_xlsx(period: str, custom_from: str = "", custom_to: str = "",
                search: str = "") -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("openpyxl не установлен. Запусти: pip install openpyxl")

    import io

    date_from, date_to = parse_period(period, custom_from, custom_to)
    shifts = get_shifts(date_from, date_to)
    if search:
        search_low = search.lower().strip()
        shifts = [s for s in shifts if search_low in s["worker_name"].lower()]

    # Build stats (same logic as render_csv)
    ledger, ledger_comments = _load_ledger(date_from, date_to, search)
    stats = _build_stats(shifts, ledger)

    wb = Workbook()
    ws = wb.active
    ws.title = "Табель"

    fill_header = PatternFill(fill_type="solid", fgColor="2D333B")
    fill_total = PatternFill(fill_type="solid", fgColor="FFD60A")
    bold = Font(bold=True)
    white_bold = Font(bold=True, color="FFFFFF")
    dark_bold = Font(bold=True, color="0D1117")

    period_label = PERIOD_LABELS.get(period, period)
    df_str = date_from.strftime("%d.%m.%Y")
    dt_str = date_to.strftime("%d.%m.%Y")

    r = 1
    ws.cell(r, 1, "ЗАРЯД · Табель учёта рабочего времени").font = Font(bold=True, size=13)
    ws.merge_cells(f"A{r}:J{r}")
    r += 1
    ws.cell(r, 1, "Период:").font = bold
    ws.cell(r, 2, f"{period_label}  {df_str} — {dt_str}")
    r += 1
    if search:
        ws.cell(r, 1, "Фильтр:").font = bold
        ws.cell(r, 2, _csv_safe(search))
        r += 1
    r += 1

    # --- Summary ---
    ws.cell(r, 1, "СВОДКА ПО РАБОТНИКАМ").font = Font(bold=True, size=11)
    ws.merge_cells(f"A{r}:L{r}")
    r += 1
    for col, h in enumerate(
        ["ФИО", "График", "Смен", "Дневная смена", "Ночная смена", "Общее время",
         "Среднее/день", "Опозданий", "Переработок", "Незакр.",
         "Штрафы, ₽", "Премии, ₽"], 1
    ):
        cell = ws.cell(r, col, h)
        cell.font = white_bold
        cell.fill = fill_header
    r += 1

    total_shifts = 0
    total_hours = 0.0
    total_day_hours = 0.0
    total_night_hours = 0.0
    total_fines = 0.0
    total_bonuses = 0.0
    for st in sorted(stats.values(), key=lambda x: x["name"]):
        closed = st["shifts"] - st["open"]
        avg = round(st["hours"] / closed, 2) if closed > 0 else 0.0
        for col, val in enumerate([
            st["name"], st["schedule"], st["shifts"],
            round(st["day_hours"], 2), round(st["night_hours"], 2), round(st["hours"], 2), avg,
            st["late"] or "", st["overtime"] or "", st["open"] or "",
            round(st["fines"], 2) or "", round(st["bonuses"], 2) or "",
        ], 1):
            ws.cell(r, col, val)
        total_shifts += st["shifts"]
        total_hours += st["hours"]
        total_day_hours += st["day_hours"]
        total_night_hours += st["night_hours"]
        total_fines += st["fines"]
        total_bonuses += st["bonuses"]
        r += 1

    for col, val in enumerate([
        "ИТОГО", "", total_shifts,
        round(total_day_hours, 2), round(total_night_hours, 2), round(total_hours, 2),
        "", "", "", "",
        round(total_fines, 2), round(total_bonuses, 2),
    ], 1):
        cell = ws.cell(r, col, val)
        cell.font = dark_bold
        cell.fill = fill_total
    r += 2

    # --- Detail ---
    ws.cell(r, 1, "ДЕТАЛИЗАЦИЯ ПО СМЕНАМ").font = Font(bold=True, size=11)
    ws.merge_cells(f"A{r}:I{r}")
    r += 1
    for col, h in enumerate(
        ["Дата", "Работник", "График", "Приход", "Уход", "Часов", "Опоздание", "Статус", "Смена"], 1
    ):
        cell = ws.cell(r, col, h)
        cell.font = white_bold
        cell.fill = fill_header
    r += 1

    for s in sorted(shifts, key=lambda x: (x["worker_name"], x["date"])):
        arr = dt.datetime.fromisoformat(s["arrived_at"])
        left_str = dt.datetime.fromisoformat(s["left_at"]).strftime("%H:%M") if s["left_at"] else ""
        h = shift_hours(s)
        late_cls, late_lbl = lateness(s)
        status = "открыта" if not s["left_at"] else ("авто" if s["auto_closed"] else "")
        for col, val in enumerate([
            arr.strftime("%d.%m.%Y"), _csv_safe(s["worker_name"]),
            f"{s['default_start'] or '?'}–{s['default_end'] or '?'}",
            arr.strftime("%H:%M"), left_str,
            round(h, 2) if h is not None else "",
            late_lbl if late_cls else "", status,
            "Ночная" if s["shift_type"] == "night" else "Дневная",
        ], 1):
            ws.cell(r, col, val)
        r += 1

    for i, width in enumerate([18, 24, 14, 14, 14, 12, 12, 10, 10, 10, 12, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # --- Штрафы и премии (отдельный лист) ---
    ws2 = wb.create_sheet("Штрафы и премии")
    r2 = 1
    ws2.cell(r2, 1, "ШТРАФЫ И ПРЕМИИ").font = Font(bold=True, size=13)
    ws2.merge_cells(f"A{r2}:I{r2}")
    r2 += 1
    ws2.cell(r2, 1, "Период:").font = bold
    ws2.cell(r2, 2, f"{period_label}  {df_str} — {dt_str}")
    r2 += 2

    for col, h in enumerate(_LEDGER_HEADERS, 1):
        cell = ws2.cell(r2, col, h)
        cell.font = white_bold
        cell.fill = fill_header
    r2 += 1

    for row in ledger:
        is_bonus = safe_kind(row["kind"]) == "bonus"
        issued = dt.datetime.fromisoformat(row["created_at"])
        for col, val in enumerate([
            dt.date.fromisoformat(row["date"]).strftime("%d.%m.%Y"),
            _csv_safe(row["worker_name"]),
            "Премия" if is_bonus else "Штраф",
            _csv_safe(row["title"]),
            round(row["amount"], 2),
            _csv_safe(row["created_by"]),
            issued.strftime("%d.%m.%Y %H:%M"),
            _csv_safe(row["description"] or ""),
            _csv_safe(_ledger_comments(row, ledger_comments)),
        ], 1):
            ws2.cell(r2, col, val)
        r2 += 1

    if not ledger:
        ws2.cell(r2, 1, "За период штрафов и премий не выдавали")
        r2 += 1

    for col, val in enumerate(
        ["ИТОГО штрафов", "", "", "", round(total_fines, 2), "", "", "", ""], 1
    ):
        cell = ws2.cell(r2, col, val)
        cell.font = dark_bold
        cell.fill = fill_total
    r2 += 1
    for col, val in enumerate(
        ["ИТОГО премий", "", "", "", round(total_bonuses, 2), "", "", "", ""], 1
    ):
        cell = ws2.cell(r2, col, val)
        cell.font = dark_bold
        cell.fill = fill_total

    for i, width in enumerate([14, 24, 12, 28, 14, 18, 18, 36, 48], 1):
        ws2.column_dimensions[get_column_letter(i)].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
