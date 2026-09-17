import datetime as dt
import html
import urllib.parse

from views.common import topbar, money
from db.fines import get_ledger, ledger_totals, safe_kind
from db.comments import get_fine_comments_bulk
from utils import parse_period

_LEDGER_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Штрафы и премии</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css?v=14">
</head><body>
{topbar}
<div class="container">

<h1>💰 Штрафы и премии</h1>
<p class="text-sm-muted">
  Только выданные штрафы и премии: кому, когда, сколько и за что.
</p>

<div class="periods">{period_links}
  <a href="#" onclick="event.preventDefault(); toggleCal()" class="{custom_active}">📅 Свой период</a>
</div>

<div id="calBlock" class="cal-block" style="{cal_display_style}">
  <form method="GET" action="/ledger" class="flex-row">
    <input type="hidden" name="period" value="custom">
    <input type="hidden" name="kind" value="{kind}">
    <label class="text-sm-muted">С:</label>
    <input type="date" name="from" value="{cal_from}" required class="input-full">
    <label class="text-sm-muted">По:</label>
    <input type="date" name="to" value="{cal_to}" required class="input-full">
    <button type="submit" class="btn btn-primary btn-sm">Показать</button>
  </form>
</div>

<p class="subtitle">Период: {date_from} — {date_to}</p>

<div class="cards">
  <div class="card"><div class="v amount-fine">−{fines_total} ₽</div><div class="l">Штрафов ({fines_count})</div></div>
  <div class="card"><div class="v amount-bonus">+{bonus_total} ₽</div><div class="l">Премий ({bonus_count})</div></div>
  <div class="card"><div class="v {balance_cls}">{balance} ₽</div><div class="l">Итого</div></div>
</div>

<form method="GET" action="/ledger" class="mb-sm">
  <input type="hidden" name="period" value="{period}">
  <input type="hidden" name="from" value="{cal_from}">
  <input type="hidden" name="to" value="{cal_to}">
  <input type="hidden" name="kind" value="{kind}">
  <input class="search" type="text" name="search" placeholder="🔍 Поиск по имени работника..."
         value="{search_value}">
</form>

<div class="filter-bar">
  <div class="filter-chips">
    <a class="filter-chip {all_active}" href="{qs_all}">Все</a>
    <a class="filter-chip {fine_active}" href="{qs_fine}">💰 Только штрафы</a>
    <a class="filter-chip {bonus_active}" href="{qs_bonus}">🎁 Только премии</a>
  </div>
  <a class="btn btn-sm" href="/export_xlsx?{export_qs}">📊 Выгрузить отчёт</a>
</div>

<div class="scroll-x">
<table>
  <thead><tr>
    <th>Дата</th><th>Работник</th><th>Тип</th><th>Название</th>
    <th>Сумма</th><th>Кто выдал</th><th>Когда выдал</th><th>Комментарий</th>{actions_head}
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>

<div class="footer">Записей: {total_rows}</div>
</div>

<div class="toast" id="toast"></div>

<script src="/static/app.js?v=1"></script>
<script>
function toggleCal() {{
  const b = document.getElementById("calBlock");
  b.style.display = (b.style.display === "none" || !b.style.display) ? "block" : "none";
}}
async function deleteFine(id, kind) {{
  if (!confirm(kind === "bonus" ? "Удалить премию?" : "Удалить штраф?")) return;
  try {{
    const r = await fetch("/api/delete_fine", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Удалено"); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || "Ошибка", true);
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
</script>
</body></html>
"""


def _comment_cell(row, comments_map: dict) -> str:
    """Описание записи + все комментарии к ней."""
    parts = []
    if row["description"]:
        parts.append(f'<div>{html.escape(row["description"])}</div>')
    for c in comments_map.get(row["id"], []):
        created = dt.datetime.fromisoformat(c["created_at"]).strftime("%d.%m.%Y %H:%M")
        parts.append(
            f'<div class="text-sm-muted mt-sm">💬 {html.escape(c["author"])} '
            f'({created}): {html.escape(c["text"])}</div>'
        )
    return "".join(parts) if parts else '<span class="text-sm-muted">—</span>'


def render_ledger(user: str, period: str, search: str = "", kind: str = "",
                  custom_from: str = "", custom_to: str = "",
                  can_delete: bool = True, role: str = "admin") -> str:
    date_from, date_to = parse_period(period, custom_from, custom_to)
    kind = kind if kind in ("fine", "bonus") else ""
    rows_data = get_ledger(date_from, date_to, kind or None, search)

    comments_map = get_fine_comments_bulk([r["id"] for r in rows_data])

    # Итоги считаем по всему периоду, а не по выбранной вкладке —
    # иначе «Только премии» обнулит сумму штрафов и баланс станет неверным.
    all_rows = rows_data if not kind else get_ledger(date_from, date_to, None, search)
    fines_total, bonus_total = ledger_totals(all_rows)
    fines_count = sum(1 for r in all_rows if safe_kind(r["kind"]) == "fine")
    bonus_count = len(all_rows) - fines_count
    balance = bonus_total - fines_total

    rows = []
    for r in rows_data:
        is_bonus = safe_kind(r["kind"]) == "bonus"
        d = dt.date.fromisoformat(r["date"])
        issued = dt.datetime.fromisoformat(r["created_at"]).strftime("%d.%m.%Y %H:%M")
        amount_html = (
            f'<span class="{"amount-bonus" if is_bonus else "amount-fine"}">'
            f'{"+" if is_bonus else "−"}{money(r["amount"])} ₽</span>'
        )
        type_html = (
            '<span class="pill bonus-amount">🎁 Премия</span>' if is_bonus
            else '<span class="pill fine-amount">💰 Штраф</span>'
        )
        actions_cell = (
            f'<td><button class="btn btn-sm btn-danger" '
            f'onclick="deleteFine({r["id"]}, \'{safe_kind(r["kind"])}\')">× Удалить</button></td>'
            if can_delete else ''
        )
        rows.append(
            f'<tr>'
            f'<td>{d.strftime("%d.%m.%Y")}</td>'
            f'<td><a href="/worker?id={r["worker_id"]}">{html.escape(r["worker_name"])}</a></td>'
            f'<td>{type_html}</td>'
            f'<td>{html.escape(r["title"])}</td>'
            f'<td>{amount_html}</td>'
            f'<td>{html.escape(r["created_by"])}</td>'
            f'<td>{issued}</td>'
            f'<td>{_comment_cell(r, comments_map)}</td>'
            f'{actions_cell}'
            f'</tr>'
        )
    colspan = 9 if can_delete else 8
    rows_html = "\n".join(rows) if rows else (
        f'<tr><td colspan="{colspan}" class="empty-cell">'
        f'За этот период ничего не выдавали</td></tr>'
    )

    def qs(**over) -> str:
        params = {"period": period, "search": search, "kind": kind,
                  "from": custom_from, "to": custom_to}
        params.update(over)
        return "/ledger?" + urllib.parse.urlencode({k: v for k, v in params.items() if v})

    base_qs = ""
    if search:
        base_qs += "&search=" + urllib.parse.quote(search)
    if kind:
        base_qs += "&kind=" + kind
    period_links = "".join(
        f'<a href="/ledger?period={p}{base_qs}" '
        f'class="{"active" if period == p else ""}">{label}</a>'
        for p, label in [
            ("today", "Сегодня"), ("week", "Неделя"),
            ("first_half", "1-15"), ("second_half", "16-конец"),
            ("this_month", "Этот месяц"), ("prev_month", "Прошлый месяц"),
            ("year", "Год"),
        ]
    )

    cal_from = custom_from if custom_from else date_from.isoformat()
    cal_to = custom_to if custom_to else date_to.isoformat()

    export_qs = f"period={period}"
    if period == "custom":
        export_qs += f"&from={urllib.parse.quote(cal_from)}&to={urllib.parse.quote(cal_to)}"
    if search:
        export_qs += "&search=" + urllib.parse.quote(search)

    return _LEDGER_PAGE.format(
        topbar=topbar("ledger", user, role),
        period_links=period_links,
        custom_active="active" if period == "custom" else "",
        cal_display_style="" if period == "custom" else "display:none;",
        cal_from=html.escape(cal_from),
        cal_to=html.escape(cal_to),
        date_from=date_from.strftime("%d.%m.%Y"),
        date_to=date_to.strftime("%d.%m.%Y"),
        period=html.escape(period),
        kind=html.escape(kind),
        search_value=html.escape(search),
        fines_total=money(fines_total),
        bonus_total=money(bonus_total),
        fines_count=fines_count,
        bonus_count=bonus_count,
        balance=("+" if balance > 0 else "−" if balance < 0 else "") + money(abs(balance)),
        balance_cls="amount-bonus" if balance > 0 else ("amount-fine" if balance < 0 else ""),
        all_active="active" if not kind else "",
        fine_active="active" if kind == "fine" else "",
        bonus_active="active" if kind == "bonus" else "",
        qs_all=html.escape(qs(kind="")),
        qs_fine=html.escape(qs(kind="fine")),
        qs_bonus=html.escape(qs(kind="bonus")),
        export_qs=html.escape(export_qs),
        actions_head="<th></th>" if can_delete else "",
        rows=rows_html,
        total_rows=len(rows_data),
    )
