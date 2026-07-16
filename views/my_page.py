import datetime as dt
import html
import json

from views.common import render_heatmap, build_heatmap_info_json
from db.workers import get_worker_by_id
from db.shifts import get_all_shifts_for_worker, get_shifts
from db.attachments import get_objects_of_worker
from utils import shift_hours, lateness, now_msk, hhmm_to_time, parse_period, PERIOD_LABELS

_MY_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · {name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css?v=11">
</head><body>

<div class="topbar">
  <div class="container topbar-inner">
    <div class="brand">
      <svg width="56" height="26" viewBox="0 0 80 36" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="6" width="68" height="24" rx="3" fill="none" stroke="#ffd60a" stroke-width="2.5"/>
        <rect x="71" y="12" width="6" height="12" rx="1.5" fill="#ffd60a"/>
        <rect x="5" y="9" width="62" height="18" rx="1.5" fill="rgba(255, 214, 10, 0.08)"/>
        <text x="36" y="22" text-anchor="middle" fill="#ffd60a"
              font-family="-apple-system, Arial, sans-serif" font-size="11"
              font-weight="800" letter-spacing="1.5">ЗАРЯД</text>
      </svg>
      <div>
        <div class="name">ЗАРЯД</div>
        <div class="sub">Личный кабинет</div>
      </div>
    </div>
    <div class="flex-1"></div>
    <div class="user-info">
      <span>👤 {name}</span>
      <a href="/logout">Выйти</a>
    </div>
  </div>
</div>

<div class="container">

<h1>{name_html}</h1>
<p class="subtitle">
  График: {schedule}
</p>

<div class="periods">{period_links}
  <a href="#" onclick="event.preventDefault(); toggleCal()" class="{custom_active}">📅 Свой период</a>
</div>

<div id="calBlock" class="cal-block" style="{cal_display_style}">
  <form method="GET" action="" class="flex-row">
    <input type="hidden" name="period" value="custom">
    <label class="text-sm-muted">С:</label>
    <input type="date" name="from" value="{cal_from}" required class="input-full">
    <label class="text-sm-muted">По:</label>
    <input type="date" name="to" value="{cal_to}" required class="input-full">
    <button type="submit" class="btn btn-primary btn-sm">Показать</button>
  </form>
</div>

<p class="subtitle">
  Период: {date_from} — {date_to}
</p>

<div class="cards">
  <div class="card"><div class="v">{period_hours}</div><div class="l">Часов за период</div></div>
  <div class="card"><div class="v">{avg_per_day}</div><div class="l">Среднее в день</div></div>
  <div class="card"><div class="v">{late_count}</div><div class="l">Опозданий</div></div>
  <div class="card"><div class="v">{overtime_count}</div><div class="l">Переработок</div></div>
</div>

{objects_block}

<h2>Календарь последних 30 дней</h2>
<div class="heatmap-wrap">
  <div class="heatmap">{heatmap}</div>
  <div class="heatmap-info" id="dayInfoPanel">
    <div class="text-sm-muted">Нажми на дату в календаре, чтобы увидеть детали</div>
  </div>
</div>

<h2>По месяцам</h2>
<div class="chart-box"><canvas id="byMonth"></canvas></div>

<h2>Мои смены · {period_label}</h2>
<div class="scroll-x">
<table>
  <thead><tr><th>Дата</th><th>Смена</th><th>Приход</th><th>Уход</th><th>Часы</th><th>Пометка</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>

<div class="footer">{name} · {total_shifts} смен за период</div>
</div>

<script src="/static/chart.min.js"></script>
<script>
function toggleCal() {{
  const b = document.getElementById("calBlock");
  b.style.display = (b.style.display === "none" || !b.style.display) ? "block" : "none";
}}
const HEATMAP_INFO = {heatmap_info_json};
function showDayInfo(dateStr, cellEl) {{
  document.querySelectorAll(".heatmap .cell.selected").forEach(c => c.classList.remove("selected"));
  if (cellEl) cellEl.classList.add("selected");
  const shifts = HEATMAP_INFO[dateStr] || [];
  const d = new Date(dateStr + "T00:00:00");
  const dateLbl = d.toLocaleDateString("ru-RU", {{day:"2-digit", month:"2-digit", year:"numeric", weekday:"long"}});
  const panel = document.getElementById("dayInfoPanel");
  let html = `<div class="heatmap-info-date">📅 ${{dateLbl}}</div>`;
  if (!shifts.length) {{
    html += '<p class="text-sm-muted">Смен в этот день нет</p>';
  }} else {{
    html += shifts.map(s => {{
      const typeLbl = s.shift_type === "night" ? "🌙 Ночная" : "☀️ Дневная";
      const hoursLbl = s.hours !== null ? `${{s.hours.toFixed(2)}} ч` : "смена открыта";
      const marks = [];
      if (s.auto) marks.push('<span class="pill auto">авто</span>');
      if (s.late) marks.push(`<span class="pill late">${{s.late}}</span>`);
      if (s.overtime) marks.push(`<span class="pill late">переработка ${{s.overtime}}</span>`);
      return '<div class="comment-card" style="margin:8px 0;">' +
        `<div class="comment-meta"><strong>${{typeLbl}}</strong></div>` +
        `<div class="comment-body">` +
        `${{s.arrived}} → ${{s.left ?? "—"}} · ${{hoursLbl}}` +
        (marks.length ? '<div class="mt-sm">' + marks.join(" ") + '</div>' : '') +
        `</div></div>`;
    }}).join("");
  }}
  panel.innerHTML = html;
}}
const opts = {{
  responsive:true, maintainAspectRatio:false,
  plugins:{{ legend:{{ labels:{{ color:"#c9d1d9" }} }} }},
  scales:{{
    x:{{ ticks:{{color:"#8b949e"}}, grid:{{color:"#30363d"}} }},
    y:{{ ticks:{{color:"#8b949e"}}, grid:{{color:"#30363d"}}, beginAtZero:true }}
  }}
}};
new Chart(document.getElementById("byMonth"), {{
  type:"bar",
  data:{{ labels:{by_month_labels}, datasets:[{{
    label:"Часов", data:{by_month_data},
    backgroundColor:"#ffd60a", borderRadius:4
  }}]}},
  options: opts
}});
</script>
</body></html>
"""


def render_my_page(worker_id: int, user: str, period: str = "today",
                   custom_from: str = "", custom_to: str = "") -> str | None:
    worker = get_worker_by_id(worker_id)
    if not worker:
        return None

    today = now_msk().date()
    date_from, date_to = parse_period(period, custom_from, custom_to)

    all_shifts = get_all_shifts_for_worker(worker_id)
    period_shifts = get_shifts(date_from, date_to, worker_id)

    by_month = {}
    for s in all_shifts:
        h = shift_hours(s)
        if h is None:
            continue
        d = dt.date.fromisoformat(s["date"])
        month_key = d.strftime("%Y-%m")
        by_month[month_key] = by_month.get(month_key, 0) + h

    period_hours = 0.0
    days_with_work = 0
    late_count = 0
    overtime_count = 0

    for s in period_shifts:
        h = shift_hours(s)
        if h is None:
            continue
        period_hours += h
        days_with_work += 1
        d = dt.date.fromisoformat(s["date"])
        late_cls, _ = lateness(s)
        if late_cls in ("late", "very-late"):
            late_count += 1
        if worker["default_end"] and s["left_at"] and s["shift_type"] != "night":
            left = dt.datetime.fromisoformat(s["left_at"])
            sched_end = hhmm_to_time(worker["default_end"])
            sched_dt = dt.datetime.combine(d, sched_end)
            if (left - sched_dt).total_seconds() > 30 * 60:
                overtime_count += 1

    avg_per_day = round(period_hours / days_with_work, 2) if days_with_work else 0
    heatmap_cells = render_heatmap(all_shifts, today)
    heatmap_info_json = build_heatmap_info_json(all_shifts, worker)

    rows = []
    for s in period_shifts:
        arr = dt.datetime.fromisoformat(s["arrived_at"])
        h = shift_hours(s)
        left_str = "—"
        if s["left_at"]:
            left_str = dt.datetime.fromisoformat(s["left_at"]).strftime("%H:%M")
        pills = []
        if s["auto_closed"]:
            pills.append('<span class="pill auto">авто</span>')
        if not s["left_at"]:
            pills.append('<span class="pill open">открыта</span>')
        late_cls, late_lbl = lateness(s)
        if late_cls and s["left_at"]:
            pills.append(f'<span class="pill {late_cls}">{late_lbl}</span>')
        shift_type_html = '🌙 Ночь' if s["shift_type"] == "night" else '☀️ День'
        rows.append(
            f'<tr><td>{arr.strftime("%d.%m.%Y")}</td>'
            f'<td>{shift_type_html}</td>'
            f'<td>{arr.strftime("%H:%M")}</td>'
            f'<td>{left_str}</td>'
            f'<td>{f"{h:.2f}" if h is not None else "—"}</td>'
            f'<td>{" ".join(pills)}</td></tr>'
        )

    by_month_sorted = sorted(by_month.items())
    bm_labels = [k for k, _ in by_month_sorted]
    bm_data = [round(v, 1) for _, v in by_month_sorted]

    attached_objects = get_objects_of_worker(worker_id, include_deleted=False)
    if attached_objects:
        pills_html = " ".join(
            f'<span class="obj-tag">📍 {html.escape(o["name"])}</span>'
            for o in attached_objects
        )
        objects_block = (
            f'<h2>📍 Мои объекты</h2>'
            f'<div class="info-block mb-lg">'
            f'<div class="flex-wrap">{pills_html}</div>'
            f'</div>'
        )
    else:
        objects_block = ""

    period_links = "".join(
        f'<a href="?period={p}" class="{"active" if period == p else ""}">{label}</a>'
        for p, label in [
            ("today", "Сегодня"), ("week", "Неделя"),
            ("first_half", "1-15"), ("second_half", "16-конец"),
            ("this_month", "Этот месяц"), ("prev_month", "Прошлый месяц"),
            ("year", "Год"),
        ]
    )
    custom_active = "active" if period == "custom" else ""
    cal_from = custom_from if custom_from else date_from.isoformat()
    cal_to = custom_to if custom_to else date_to.isoformat()
    cal_display_style = "" if period == "custom" else "display:none;"

    return _MY_PAGE.format(
        name=html.escape(worker["name"]),
        name_html=html.escape(worker["name"]),
        schedule=f"{worker['default_start']}-{worker['default_end']}",
        period_links=period_links,
        custom_active=custom_active,
        cal_from=html.escape(cal_from),
        cal_to=html.escape(cal_to),
        cal_display_style=cal_display_style,
        date_from=date_from.strftime("%d.%m.%Y"),
        date_to=date_to.strftime("%d.%m.%Y"),
        period_label=html.escape(PERIOD_LABELS.get(period, period)),
        period_hours=f"{period_hours:.1f}",
        avg_per_day=f"{avg_per_day:.1f}",
        late_count=late_count,
        overtime_count=overtime_count,
        objects_block=objects_block,
        heatmap="\n".join(heatmap_cells),
        heatmap_info_json=heatmap_info_json,
        rows="\n".join(rows) if rows else
            '<tr><td colspan="6" class="empty-cell">Нет смен за период</td></tr>',
        by_month_labels=json.dumps(bm_labels),
        by_month_data=json.dumps(bm_data),
        total_shifts=len(period_shifts),
    )
