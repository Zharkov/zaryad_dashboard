import datetime as dt
import html as _html
import json

from utils import shift_hours, lateness, hhmm_to_time

LOGO_SVG = """<svg width="56" height="26" viewBox="0 0 80 36" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="6" width="68" height="24" rx="3" fill="none" stroke="#ffd60a" stroke-width="2.5"/>
  <rect x="71" y="12" width="6" height="12" rx="1.5" fill="#ffd60a"/>
  <rect x="5" y="9" width="62" height="18" rx="1.5" fill="rgba(255, 214, 10, 0.08)"/>
  <text x="36" y="22" text-anchor="middle" fill="#ffd60a"
        font-family="-apple-system, Arial, sans-serif" font-size="11"
        font-weight="800" letter-spacing="1.5">ЗАРЯД</text>
</svg>"""


def topbar(active: str, user: str, role: str = "admin") -> str:
    def cls(name):
        return "active" if active == name else ""
    if role == "accountant":
        nav = f'<a href="/" class="{cls("dashboard")}">Дашборд</a>'
    else:
        nav = (
            f'<a href="/" class="{cls("dashboard")}">Дашборд</a>'
            f'<a href="/workers" class="{cls("workers")}">Работники</a>'
            f'<a href="/objects" class="{cls("objects")}">Объекты</a>'
            f'<a href="/users" class="{cls("users")}">Пользователи</a>'
        )
    return f"""
<div class="topbar">
  <div class="container topbar-inner">
    <a href="/" class="brand">
      {LOGO_SVG}
      <div>
        <div class="name">ЗАРЯД</div>
        <div class="sub">Табель</div>
      </div>
    </a>
    <div class="nav" id="mainNav">{nav}</div>
    <div class="user-info">
      <span>👤 {_html.escape(user)}</span>
      <a href="/logout">Выйти</a>
    </div>
    <button class="burger" id="burgerBtn" aria-label="Меню">☰</button>
  </div>
</div>
<button class="scroll-top" id="scrollTopBtn" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" title="Наверх" aria-label="Наверх">↑</button>
<script src="/static/app.js?v=1"></script>
<script>
(function(){{
  var nav = document.getElementById('mainNav');
  var burger = document.getElementById('burgerBtn');
  burger.addEventListener('click', function(e){{
    e.stopPropagation();
    nav.classList.toggle('open');
  }});
  nav.querySelectorAll('a').forEach(function(a){{
    a.addEventListener('click', function(){{ nav.classList.remove('open'); }});
  }});
  document.addEventListener('click', function(e){{
    if (!nav.contains(e.target) && e.target !== burger) nav.classList.remove('open');
  }});
  var scrollBtn = document.getElementById('scrollTopBtn');
  window.addEventListener('scroll', function(){{
    scrollBtn.classList.toggle('visible', window.scrollY > 300);
  }}, {{passive: true}});
}})();
</script>
"""


def render_heatmap(all_shifts, today: dt.date) -> list[str]:
    shift_by_date: dict[dt.date, float] = {}
    for s in all_shifts:
        if not s["left_at"]:
            continue
        d = dt.date.fromisoformat(s["date"])
        shift_by_date[d] = shift_by_date.get(d, 0) + (shift_hours(s) or 0)

    cells = []
    start = today - dt.timedelta(days=27)
    start = start - dt.timedelta(days=start.weekday())
    d = start
    while d <= today:
        is_weekend = d.weekday() >= 5
        h = shift_by_date.get(d)
        cls = "cell"
        if is_weekend and h is None:
            cls += " weekend"
            hour_str = ""
        elif h is None:
            hour_str = ""
        else:
            if h >= 10:
                cls += " l4"
            elif h >= 8:
                cls += " l3"
            elif h >= 6:
                cls += " l2"
            else:
                cls += " l1"
            hour_str = f'{h:.1f}ч'
        title = d.strftime("%d.%m.%Y")
        if h is not None:
            title += f" · {h}ч"
        elif is_weekend:
            title += " · выходной"
        else:
            title += " · нет данных"
        cells.append(
            f'<div class="{cls}" title="{title}" '
            f'onclick="showDayInfo(\'{d.isoformat()}\', this)">'
            f'<span class="d">{d.day}</span>'
            f'<span class="h">{hour_str}</span>'
            f'</div>'
        )
        d += dt.timedelta(days=1)
    return cells


def build_heatmap_info_json(all_shifts, worker) -> str:
    info: dict[str, list[dict]] = {}
    for s in all_shifts:
        arr = dt.datetime.fromisoformat(s["arrived_at"])
        h = shift_hours(s)
        late_cls, late_lbl = lateness(s)
        overtime_lbl = ""
        if (worker["default_end"] and s["left_at"] and s["shift_type"] != "night"):
            d = dt.date.fromisoformat(s["date"])
            left = dt.datetime.fromisoformat(s["left_at"])
            sched_dt = dt.datetime.combine(d, hhmm_to_time(worker["default_end"]))
            diff_min = int((left - sched_dt).total_seconds() / 60)
            if diff_min > 30:
                overtime_lbl = f"+{diff_min}мин"
        info.setdefault(s["date"], []).append({
            "shift_type": s["shift_type"] or "day",
            "arrived": arr.strftime("%H:%M"),
            "left": dt.datetime.fromisoformat(s["left_at"]).strftime("%H:%M") if s["left_at"] else None,
            "hours": round(h, 2) if h is not None else None,
            "auto": bool(s["auto_closed"]),
            "late": late_lbl if late_cls in ("late", "very-late") else "",
            "overtime": overtime_lbl,
        })
    return json.dumps(info, ensure_ascii=False)
