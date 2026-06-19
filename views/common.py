import datetime as dt
import html as _html

from utils import shift_hours

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
    <div class="nav">{nav}</div>
    <div class="user-info">
      <span>👤 {_html.escape(user)}</span>
      <a href="/logout">Выйти</a>
    </div>
  </div>
</div>
"""


def render_heatmap(all_shifts, today: dt.date) -> list[str]:
    shift_by_date = {dt.date.fromisoformat(s["date"]): shift_hours(s)
                     for s in all_shifts if s["left_at"]}
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
            f'<div class="{cls}" title="{title}">'
            f'<span class="d">{d.day}</span>'
            f'<span class="h">{hour_str}</span>'
            f'</div>'
        )
        d += dt.timedelta(days=1)
    return cells
