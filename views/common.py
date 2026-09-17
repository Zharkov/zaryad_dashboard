import datetime as dt
import html as _html
import json

from db.fines import safe_kind
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
    if role == "manager":
        nav = f'<a href="/" class="{cls("dashboard")}">Дашборд</a>'
    elif role == "accountant":
        nav = (
            f'<a href="/" class="{cls("dashboard")}">Дашборд</a>'
            f'<a href="/ledger" class="{cls("ledger")}">Штрафы и премии</a>'
        )
    else:
        nav = (
            f'<a href="/" class="{cls("dashboard")}">Дашборд</a>'
            f'<a href="/workers" class="{cls("workers")}">Работники</a>'
            f'<a href="/objects" class="{cls("objects")}">Объекты</a>'
            f'<a href="/crews" class="{cls("crews")}">Бригады</a>'
            f'<a href="/ledger" class="{cls("ledger")}">Штрафы и премии</a>'
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


def money(amount: float) -> str:
    """1000 → «1 000»"""
    return f'{amount:,.0f}'.replace(",", " ")


def render_heatmap(all_shifts, today: dt.date, fines=None) -> list[str]:
    shift_by_date: dict[dt.date, float] = {}
    for s in all_shifts:
        if not s["left_at"]:
            continue
        d = dt.date.fromisoformat(s["date"])
        shift_by_date[d] = shift_by_date.get(d, 0) + (shift_hours(s) or 0)

    fine_dates = {f["date"] for f in (fines or []) if safe_kind(f["kind"]) == "fine"}
    bonus_dates = {f["date"] for f in (fines or []) if safe_kind(f["kind"]) == "bonus"}

    cells = []
    start = today - dt.timedelta(days=27)
    start = start - dt.timedelta(days=start.weekday())
    d = start
    while d <= today:
        is_weekend = d.weekday() >= 5
        h = shift_by_date.get(d)
        has_fine = d.isoformat() in fine_dates
        has_bonus = d.isoformat() in bonus_dates
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
        if has_fine:
            cls += " has-fine"
        if has_bonus:
            cls += " has-bonus"
        title = d.strftime("%d.%m.%Y")
        if h is not None:
            title += f" · {h}ч"
        elif is_weekend:
            title += " · выходной"
        else:
            title += " · нет данных"
        if has_fine:
            title += " · есть штраф"
        if has_bonus:
            title += " · есть премия"
        cells.append(
            f'<div class="{cls}" title="{title}" '
            f'onclick="showDayInfo(\'{d.isoformat()}\', this)">'
            f'<span class="d">{d.day}</span>'
            f'<span class="h">{hour_str}</span>'
            f'</div>'
        )
        d += dt.timedelta(days=1)
    return cells


def build_heatmap_info_json(all_shifts, worker, fines=None) -> str:
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
            "kind": "shift",
            "shift_type": s["shift_type"] or "day",
            "arrived": arr.strftime("%H:%M"),
            "left": dt.datetime.fromisoformat(s["left_at"]).strftime("%H:%M") if s["left_at"] else None,
            "hours": round(h, 2) if h is not None else None,
            "auto": bool(s["auto_closed"]),
            "late": late_lbl if late_cls in ("late", "very-late") else "",
            "overtime": overtime_lbl,
        })
    for f in (fines or []):
        info.setdefault(f["date"], []).append({
            "kind": safe_kind(f["kind"]),
            "title": f["title"],
            "description": f["description"] or "",
            "amount": f["amount"],
        })
    return json.dumps(info, ensure_ascii=False)


def render_fine_cards(fines, comments_map: dict, can_delete: bool,
                      empty_text: str = "Штрафов нет") -> str:
    if not fines:
        return f'<p class="text-sm-muted">{empty_text}</p>'
    cards = []
    for f in fines:
        kind = safe_kind(f["kind"])
        is_bonus = kind == "bonus"
        created = dt.date.fromisoformat(f["date"])
        amount_str = ("+" if is_bonus else "−") + money(f["amount"])
        icon = "🎁" if is_bonus else "💰"
        card_cls = "bonus-card" if is_bonus else "fine-card"
        amount_cls = "bonus-amount" if is_bonus else "fine-amount"
        issued_by = "Начислил" if is_bonus else "Выдал"
        delete_btn = (
            f'<button class="btn btn-sm btn-danger" '
            f'onclick="deleteFine({f["id"]}, \'{kind}\')">× Удалить</button>'
            if can_delete else ''
        )
        desc_html = (
            f'<div class="comment-body">{_html.escape(f["description"])}</div>'
            if f["description"] else ''
        )
        comments = comments_map.get(f["id"], [])
        comment_cards = "".join(
            f'<div class="comment-card" style="margin:6px 0 0;">'
            f'<div class="comment-meta">'
            f'<span class="comment-author">👤 {_html.escape(c["author"])}</span>'
            f'<span class="comment-date">'
            f'{dt.datetime.fromisoformat(c["created_at"]).strftime("%d.%m.%Y %H:%M")}</span>'
            f'</div>'
            f'<div class="comment-body">{_html.escape(c["text"])}</div>'
            f'</div>'
            for c in comments
        )
        issued_at = dt.datetime.fromisoformat(f["created_at"]).strftime("%d.%m.%Y %H:%M")
        cards.append(
            f'<div class="comment-card {card_cls}">'
            f'<div class="comment-meta">'
            f'<span class="comment-author">{icon} {_html.escape(f["title"])}</span>'
            f'<span class="comment-date">{created.strftime("%d.%m.%Y")}</span>'
            f'<span class="pill {amount_cls}">{amount_str} ₽</span>'
            f'{delete_btn}'
            f'</div>'
            f'{desc_html}'
            f'<div class="text-sm-muted mt-sm">'
            f'{issued_by}: {_html.escape(f["created_by"])} · {issued_at}</div>'
            f'<div class="fine-comments-list mt-sm">{comment_cards}</div>'
            f'<textarea class="textarea-full mt-sm" rows="2" id="fineCommentInput{f["id"]}" '
            f'placeholder="Оставить комментарий..."></textarea>'
            f'<button class="btn btn-sm btn-primary mt-sm" '
            f'onclick="submitFineComment({f["id"]})">💬 Добавить</button>'
            f'</div>'
        )
    return "\n".join(cards)
