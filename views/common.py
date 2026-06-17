import datetime as dt
import html as _html

from utils import shift_hours

COMMON_CSS = """
:root {
  --bg: #0f1419; --surf: #161b22; --surf2: #21262d; --border: #30363d;
  --text: #e6edf3; --muted: #8b949e; --dim: #6e7681;
  --brand: #ffd60a; --brand-dark: #c9a800;
  --ok: #3fb950; --warn: #d29922; --bad: #f85149; --info: #58a6ff;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       background: var(--bg); color: var(--text);
       -webkit-font-smoothing: antialiased; }
a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }

.container { max-width: 1200px; margin: 0 auto; padding: 0 16px; }

.topbar { background: var(--surf); border-bottom: 1px solid var(--border);
          padding: 12px 0; margin-bottom: 16px; position: sticky; top: 0; z-index: 50; }
.topbar-inner { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.brand .name { font-size: 20px; font-weight: 800; letter-spacing: 1.5px;
               color: var(--brand); line-height: 1; }
.brand .sub { font-size: 10px; color: var(--muted); margin-top: 3px;
              text-transform: uppercase; letter-spacing: 1px; }
.nav { display: flex; gap: 6px; flex: 1; flex-wrap: wrap; }
.nav a { padding: 6px 12px; border-radius: 6px; color: var(--text);
         font-size: 13px; }
.nav a:hover { background: var(--surf2); text-decoration: none; }
.nav a.active { background: var(--brand); color: #000; font-weight: 600; }
.user-info { display: flex; align-items: center; gap: 10px; font-size: 13px;
             color: var(--muted); }
.user-info a { color: var(--muted); }

h1 { font-size: 22px; margin: 8px 0 16px; }
h2 { font-size: 13px; margin: 24px 0 12px; color: var(--muted);
     font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }

.btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px;
       border-radius: 6px; font-size: 13px; cursor: pointer;
       background: var(--surf2); color: var(--text); border: 1px solid var(--border);
       text-decoration: none; font-family: inherit; transition: all 0.1s; }
.btn:hover { background: var(--border); text-decoration: none; }
.btn-primary { background: var(--brand); color: #000; border-color: var(--brand);
               font-weight: 600; }
.btn-primary:hover { background: #ffe44d; color: #000; }
.btn-danger { background: rgba(248, 81, 73, 0.15); color: var(--bad);
              border-color: rgba(248, 81, 73, 0.4); }
.btn-danger:hover { background: rgba(248, 81, 73, 0.3); }
.btn-sm { padding: 4px 10px; font-size: 12px; }

.actions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }

.periods { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.periods a { padding: 6px 12px; background: var(--surf2); color: var(--text);
             border-radius: 6px; font-size: 13px; border: 1px solid var(--border); }
.periods a.active { background: var(--brand); color: #000;
                    border-color: var(--brand); font-weight: 600; }
.periods a:hover { background: var(--border); text-decoration: none; }
.periods a.active:hover { background: #ffe44d; }

.cal-block { background: var(--surf); padding: 12px 14px; border-radius: 8px;
             border: 1px solid var(--border); margin-bottom: 14px;
             border-left: 3px solid var(--brand); }
.cal-block input[type=date]:focus { outline: none; border-color: var(--brand); }
.cal-block input[type=date]::-webkit-calendar-picker-indicator {
  filter: invert(0.7);
}

.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
         gap: 10px; margin-bottom: 20px; }
.card { background: var(--surf); padding: 14px; border-radius: 8px;
        border: 1px solid var(--border); }
.card .v { font-size: 22px; font-weight: 700; color: var(--brand); }
.card .l { font-size: 11px; color: var(--muted); margin-top: 4px;
           text-transform: uppercase; letter-spacing: 1px; }

.open-shifts { background: var(--surf); padding: 12px 14px; border-radius: 8px;
               border: 1px solid var(--border); margin-bottom: 20px;
               border-left: 3px solid var(--brand); }
.open-shifts strong { color: var(--brand); }
.open-shifts ul { margin: 6px 0 0; padding-left: 20px; }
.open-shifts li { padding: 3px 0; }

.search { width: 100%; padding: 10px 14px; background: var(--surf);
          border: 1px solid var(--border); border-radius: 8px; color: var(--text);
          font-size: 14px; margin-bottom: 12px; font-family: inherit; }
.search:focus { outline: none; border-color: var(--brand); }

table { width: 100%; border-collapse: collapse; background: var(--surf);
        border-radius: 8px; overflow: hidden; border: 1px solid var(--border);
        font-size: 14px; }
th, td { padding: 10px 12px; text-align: left;
         border-bottom: 1px solid var(--border); }
th { background: var(--surf2); font-weight: 600; color: var(--muted);
     text-transform: uppercase; font-size: 11px; letter-spacing: 1px;
     position: sticky; top: 0; }
tr:last-child td { border-bottom: none; }
tr.auto { background: rgba(255, 193, 7, 0.06); }
tr.open { background: rgba(255, 214, 10, 0.04); }
tr.hover-row:hover { background: rgba(255, 214, 10, 0.05); cursor: pointer; }

.pill { display: inline-block; padding: 2px 8px; border-radius: 12px;
        font-size: 11px; font-weight: 600; }
.pill.auto { background: rgba(210, 153, 34, 0.2); color: var(--warn); }
.pill.open { background: rgba(255, 214, 10, 0.15); color: var(--brand); }
.pill.early { background: rgba(63, 185, 80, 0.15); color: var(--ok); }
.pill.late { background: rgba(210, 153, 34, 0.2); color: var(--warn); }
.pill.very-late { background: rgba(248, 81, 73, 0.2); color: var(--bad); }

.chart-box { background: var(--surf); padding: 16px; border-radius: 8px;
             border: 1px solid var(--border); margin-bottom: 16px; }
canvas { max-height: 300px; }

.footer { text-align: center; color: var(--dim); font-size: 12px;
          margin: 32px 0 16px; padding-top: 16px; border-top: 1px solid var(--border); }

.modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 200;
            display: none; align-items: flex-start; justify-content: center;
            padding: 40px 16px 16px; overflow-y: auto; }
.modal-bg.show { display: flex; }
.modal { background: var(--surf); border-radius: 10px; border: 1px solid var(--border);
         padding: 20px; max-width: 900px; width: 100%; max-height: calc(100vh - 56px);
         overflow-y: auto; }
.modal.narrow { max-width: 500px; }
.modal h3 { margin: 0 0 14px; font-size: 17px; }
.modal .row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.modal label { font-size: 13px; color: var(--muted); }
.modal input[type=time],
.modal input[type=text],
.modal input[type=date] {
  background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 7px 10px; color: var(--text); font-size: 14px; font-family: inherit;
}
.modal .footer-btns { display: flex; gap: 8px; justify-content: flex-end;
                       margin-top: 20px; flex-wrap: wrap; }

.workers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 6px; margin: 12px 0; max-height: 350px; overflow-y: auto;
                padding: 4px; }
.worker-chk { display: flex; align-items: center; gap: 8px; padding: 8px 10px;
              background: var(--bg); border-radius: 6px; cursor: pointer;
              font-size: 13px; border: 1px solid transparent; }
.worker-chk:hover { background: var(--surf2); }
.worker-chk input[type=checkbox] { accent-color: var(--brand); }
.worker-chk.selected { background: rgba(255, 214, 10, 0.1); border-color: var(--brand); }

.time-presets { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.time-presets button { padding: 6px 12px; background: var(--surf2);
                       border: 1px solid var(--border); color: var(--text);
                       border-radius: 6px; cursor: pointer; font-size: 13px;
                       font-family: inherit; }
.time-presets button.selected { background: var(--brand); color: #000;
                                  border-color: var(--brand); font-weight: 600; }

.toast { position: fixed; bottom: 20px; right: 20px; background: var(--surf);
         padding: 12px 18px; border-radius: 8px; border-left: 3px solid var(--ok);
         z-index: 300; max-width: 320px; box-shadow: 0 4px 16px rgba(0,0,0,0.5);
         font-size: 14px; transform: translateY(120%); transition: transform 0.3s; }
.toast.show { transform: translateY(0); }
.toast.error { border-left-color: var(--bad); }

.heatmap { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
           max-width: 500px; margin: 16px 0; }
.heatmap .cell { aspect-ratio: 1; border-radius: 4px; background: var(--surf2);
                 padding: 4px; display: flex; flex-direction: column;
                 justify-content: space-between; font-size: 11px; cursor: help; }
.heatmap .cell.l1 { background: rgba(255, 214, 10, 0.25); }
.heatmap .cell.l2 { background: rgba(255, 214, 10, 0.5); }
.heatmap .cell.l3 { background: rgba(255, 214, 10, 0.75); }
.heatmap .cell.l4 { background: var(--brand); color: #000; }
.heatmap .cell.weekend { background: rgba(255,255,255,0.02); }
.heatmap .cell .d { font-weight: 600; opacity: 0.7; }
.heatmap .cell .h { font-weight: 700; text-align: right; font-size: 12px; }
.heatmap .cell.l4 .d { opacity: 0.8; color: #000; }

@media (max-width: 640px) {
  .container { padding: 0 12px; }
  .topbar-inner { gap: 8px; }
  .brand .name { font-size: 17px; letter-spacing: 1px; }
  .brand .sub { display: none; }
  h1 { font-size: 18px; }
  .nav { width: 100%; order: 3; }
  .nav a { font-size: 12px; padding: 5px 9px; }
  .card .v { font-size: 18px; }
  table { font-size: 12px; }
  th, td { padding: 7px 6px; }
  th { font-size: 10px; }
  .periods a { font-size: 12px; padding: 5px 9px; }
  .btn { padding: 6px 10px; font-size: 12px; }
  .modal { padding: 16px; }
  .workers-grid { grid-template-columns: 1fr 1fr; max-height: 280px; }
}

@media (max-width: 400px) {
  .workers-grid { grid-template-columns: 1fr; }
  .cards { grid-template-columns: 1fr 1fr; }
}
"""

LOGO_SVG = """<svg width="56" height="26" viewBox="0 0 80 36" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="6" width="68" height="24" rx="3" fill="none" stroke="#ffd60a" stroke-width="2.5"/>
  <rect x="71" y="12" width="6" height="12" rx="1.5" fill="#ffd60a"/>
  <rect x="5" y="9" width="62" height="18" rx="1.5" fill="rgba(255, 214, 10, 0.08)"/>
  <text x="36" y="22" text-anchor="middle" fill="#ffd60a"
        font-family="-apple-system, Arial, sans-serif" font-size="11"
        font-weight="800" letter-spacing="1.5">ЗАРЯД</text>
</svg>"""


def topbar(active: str, user: str) -> str:
    def cls(name):
        return "active" if active == name else ""
    return f"""
<div class="topbar">
  <div class="container topbar-inner">
    <a href="/" class="brand" style="text-decoration:none;">
      {LOGO_SVG}
      <div>
        <div class="name">ЗАРЯД</div>
        <div class="sub">Табель</div>
      </div>
    </a>
    <div class="nav">
      <a href="/" class="{cls('dashboard')}">Дашборд</a>
      <a href="/workers" class="{cls('workers')}">Работники</a>
      <a href="/objects" class="{cls('objects')}">Объекты</a>
    </div>
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
