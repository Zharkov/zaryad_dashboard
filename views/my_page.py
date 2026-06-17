import datetime as dt
import html
import json

from views.common import COMMON_CSS, render_heatmap
from db.workers import get_worker_by_id
from db.shifts import get_all_shifts_for_worker
from db.attachments import get_objects_of_worker
from utils import shift_hours, lateness, now_msk, hhmm_to_time

_MY_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · {name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{css}</style>
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
    <div style="flex:1;"></div>
    <div class="user-info">
      <span>👤 {name}</span>
      <a href="/logout">Выйти</a>
    </div>
  </div>
</div>

<div class="container">

<h1>{name_html}</h1>
<p style="color:var(--muted); margin-top:-8px;">
  График: {schedule}
</p>

<div class="cards">
  <div class="card"><div class="v">{total_hours}</div><div class="l">Часов всего</div></div>
  <div class="card"><div class="v">{this_month_h}</div><div class="l">В этом месяце</div></div>
  <div class="card"><div class="v">{avg_per_day}</div><div class="l">Среднее в день</div></div>
  <div class="card"><div class="v">{late_count}</div><div class="l">Опозданий</div></div>
  <div class="card"><div class="v">{overtime_count}</div><div class="l">Переработок</div></div>
</div>

{objects_block}

<h2>Календарь последних 30 дней</h2>
<div class="heatmap">{heatmap}</div>

<h2>По месяцам</h2>
<div class="chart-box"><canvas id="byMonth"></canvas></div>

<h2>Мои смены</h2>
<div style="overflow-x:auto;">
<table>
  <thead><tr><th>Дата</th><th>Приход</th><th>Уход</th><th>Часы</th><th>Пометка</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>

<div class="footer">{name} · {total_shifts} смен</div>
</div>

<script>
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


def render_my_page(worker_id: int, user: str) -> str | None:
    worker = get_worker_by_id(worker_id)
    if not worker:
        return None

    all_shifts = get_all_shifts_for_worker(worker_id)

    total_hours = 0.0
    today = now_msk().date()
    this_month_start = today.replace(day=1)
    this_month_hours = 0.0
    days_with_work = 0
    late_count = 0
    overtime_count = 0
    by_month = {}

    for s in all_shifts:
        h = shift_hours(s)
        if h is None:
            continue
        total_hours += h
        days_with_work += 1
        d = dt.date.fromisoformat(s["date"])
        if d >= this_month_start:
            this_month_hours += h
        month_key = d.strftime("%Y-%m")
        by_month[month_key] = by_month.get(month_key, 0) + h
        late_cls, _ = lateness(s)
        if late_cls in ("late", "very-late"):
            late_count += 1
        if worker["default_end"] and s["left_at"]:
            left = dt.datetime.fromisoformat(s["left_at"])
            sched_end = hhmm_to_time(worker["default_end"])
            sched_dt = dt.datetime.combine(d, sched_end)
            if (left - sched_dt).total_seconds() > 30 * 60:
                overtime_count += 1

    avg_per_day = round(total_hours / days_with_work, 2) if days_with_work else 0
    heatmap_cells = render_heatmap(all_shifts, today)

    rows = []
    for s in all_shifts[:50]:
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
        rows.append(
            f'<tr><td>{arr.strftime("%d.%m.%Y")}</td>'
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
            f'<span class="pill" style="background:rgba(255, 214, 10, 0.15); '
            f'color:var(--brand); padding:4px 12px;">📍 {html.escape(o["name"])}</span>'
            for o in attached_objects
        )
        objects_block = (
            f'<h2>📍 Мои объекты</h2>'
            f'<div style="background:var(--surf); padding:12px 14px; border-radius:8px;'
            f'border:1px solid var(--border); margin-bottom:16px;">'
            f'<div style="display:flex; flex-wrap:wrap; gap:8px;">{pills_html}</div>'
            f'</div>'
        )
    else:
        objects_block = ""

    return _MY_PAGE.format(
        css=COMMON_CSS,
        name=html.escape(worker["name"]),
        name_html=html.escape(worker["name"]),
        schedule=f"{worker['default_start']}-{worker['default_end']}",
        total_hours=f"{total_hours:.1f}",
        this_month_h=f"{this_month_hours:.1f}",
        avg_per_day=f"{avg_per_day:.1f}",
        late_count=late_count,
        overtime_count=overtime_count,
        objects_block=objects_block,
        heatmap="\n".join(heatmap_cells),
        rows="\n".join(rows) if rows else
            '<tr><td colspan="5" style="text-align:center;color:var(--muted);">Нет смен</td></tr>',
        by_month_labels=json.dumps(bm_labels),
        by_month_data=json.dumps(bm_data),
        total_shifts=len(all_shifts),
    )
