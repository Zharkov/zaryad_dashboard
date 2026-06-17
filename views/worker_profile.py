import datetime as dt
import html
import json

from views.common import COMMON_CSS, topbar, render_heatmap
from db.workers import get_worker_by_id
from db.shifts import get_all_shifts_for_worker
from db.objects import get_objects
from db.attachments import get_objects_of_worker
from utils import shift_hours, lateness, now_msk, hhmm_to_time

_WORKER_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · {name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{css}</style>
</head><body>
{topbar}
<div class="container">
<a href="/" style="font-size:13px; color:var(--muted);">← Дашборд</a>
<h1>{name_html}</h1>
<p style="color:var(--muted); margin-top:-8px;">
  График: {schedule} {status_pill}
</p>

<div class="actions">
  <button class="btn btn-primary" onclick="openAddShift()">📝 Добавить смену</button>
</div>

<div class="cards">
  <div class="card"><div class="v">{total_hours}</div><div class="l">Часов всего</div></div>
  <div class="card"><div class="v">{this_month_h}</div><div class="l">В этом месяце</div></div>
  <div class="card"><div class="v">{avg_per_day}</div><div class="l">Среднее в день</div></div>
  <div class="card"><div class="v">{late_count}</div><div class="l">Опозданий</div></div>
  <div class="card"><div class="v">{overtime_count}</div><div class="l">Переработок</div></div>
</div>

<h2>📍 Объекты ({attached_count})</h2>
<div style="background:var(--surf); padding:12px 14px; border-radius:8px;
            border:1px solid var(--border); margin-bottom:16px;">
  <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center;">
    {attached_objects_pills}
    <button class="btn btn-sm btn-primary" onclick="openAttachObj()">📍 Прикрепить</button>
  </div>
</div>

<h2>Календарь последних 30 дней</h2>
<div class="heatmap">{heatmap}</div>

<h2>По месяцам</h2>
<div class="chart-box"><canvas id="byMonth"></canvas></div>

<h2>История смен · клик для правки</h2>
<div style="overflow-x:auto;">
<table>
  <thead><tr><th>Дата</th><th>Приход</th><th>Уход</th><th>Часы</th><th>Пометка</th><th></th></tr></thead>
  <tbody>{rows}</tbody>
</table>
</div>

<div class="footer">{name} · {total_shifts} смен</div>
</div>

<div class="modal-bg" id="modalAddShift" onclick="if(event.target===this)closeAddShift()">
  <div class="modal narrow">
    <h3>📝 Добавить смену · {name}</h3>
    <div class="row" style="flex-wrap:wrap; gap:10px;">
      <div>
        <label style="display:block; font-size:12px; color:var(--muted);">Дата:</label>
        <input type="date" id="asDate">
      </div>
      <div>
        <label style="display:block; font-size:12px; color:var(--muted);">Приход:</label>
        <input type="time" id="asArr" value="{default_start}">
      </div>
      <div>
        <label style="display:block; font-size:12px; color:var(--muted);">Уход:</label>
        <input type="time" id="asLeft" value="{default_end}">
      </div>
    </div>
    <div style="font-size:12px; color:var(--muted); margin-top:10px;">
      Время прихода/ухода взято из графика. Уход можно стереть — смена будет открытой.
    </div>
    <div style="font-size:12px; color:var(--warn); margin-top:6px;">
      ⚠ Если запись за эту дату уже есть — добавление не пройдёт. Открой её в детализации для редактирования.
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAddShift()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAddShift()">Создать</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalEditShiftPF" onclick="if(event.target===this)closeEditPF()">
  <div class="modal narrow">
    <h3 id="editTitlePF">Редактирование смены</h3>
    <div class="row">
      <label style="width:80px;">Приход:</label>
      <input type="time" id="editArrPF">
    </div>
    <div class="row">
      <label style="width:80px;">Уход:</label>
      <input type="time" id="editLeftPF">
    </div>
    <div style="color:var(--muted); font-size:12px; margin-top:8px;">
      Оставь поле пустым чтобы не менять
    </div>
    <div id="editReopenBoxPF" style="margin-top:10px; padding:10px;
         background:rgba(255, 214, 10, 0.08); border-radius:6px;
         border-left:3px solid var(--brand); display:none;">
      <div style="font-size:13px; margin-bottom:8px;">
        Сделать смену снова открытой? Уход будет стёрт, работник станет «на работе».
      </div>
      <button class="btn btn-sm" onclick="reopenShiftPF()" style="background:var(--brand); color:#000;">
        🕘 Снова открыть смену
      </button>
    </div>
    <div class="footer-btns">
      <button class="btn btn-danger" onclick="deleteShiftPF()">🗑 Удалить</button>
      <button class="btn" onclick="closeEditPF()">Отмена</button>
      <button class="btn btn-primary" onclick="submitEditPF()">Сохранить</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalAttachObj" onclick="if(event.target===this)closeAttachObj()">
  <div class="modal">
    <h3>📍 Прикрепить {name} к объектам</h3>
    <p style="color:var(--muted); font-size:13px;">
      Отметь объекты к которым работник прикреплён. Сними галку — открепить.
    </p>
    <div style="display:flex; gap:8px; margin: 8px 0;">
      <input class="search" id="aoSearch" type="text" placeholder="🔍 Поиск..."
             oninput="aoRender()" style="margin:0;">
    </div>
    <div class="workers-grid" id="aoGrid"></div>
    <div style="font-size:12px; color:var(--muted);" id="aoCount">Выбрано: 0</div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAttachObj()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAttachObj()">Сохранить</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const WORKER_ID = {worker_id};
const ALL_OBJECTS = {objects_json};
const ATTACHED_OBJ_IDS = new Set({attached_obj_ids});

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}}

function openAttachObj() {{
  document.getElementById("aoSearch").value = "";
  aoRender();
  document.getElementById("modalAttachObj").classList.add("show");
}}
function closeAttachObj() {{ document.getElementById("modalAttachObj").classList.remove("show"); }}

function aoRender() {{
  const grid = document.getElementById("aoGrid");
  const search = (document.getElementById("aoSearch").value || "").toLowerCase();
  const currentState = new Map();
  grid.querySelectorAll("input[type=checkbox]").forEach(cb => {{
    currentState.set(parseInt(cb.value), cb.checked);
  }});
  grid.innerHTML = "";
  if (ALL_OBJECTS.length === 0) {{
    grid.innerHTML = '<div style="color:var(--muted); padding:12px;">Объектов пока нет. <a href="/objects">Создать</a></div>';
    return;
  }}
  ALL_OBJECTS.filter(o => !search || o.name.toLowerCase().includes(search))
    .forEach(o => {{
      const lbl = document.createElement("label");
      lbl.className = "worker-chk";
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.value = o.id;
      const initial = currentState.has(o.id) ? currentState.get(o.id) : ATTACHED_OBJ_IDS.has(o.id);
      cb.checked = initial;
      cb.addEventListener("change", () => {{
        lbl.classList.toggle("selected", cb.checked);
        aoUpdateCount();
      }});
      if (initial) lbl.classList.add("selected");
      const sp = document.createElement("span");
      sp.textContent = o.name;
      lbl.appendChild(cb); lbl.appendChild(sp);
      grid.appendChild(lbl);
    }});
  aoUpdateCount();
}}
function aoUpdateCount() {{
  const n = document.querySelectorAll("#aoGrid input:checked").length;
  document.getElementById("aoCount").textContent = "Выбрано: " + n;
}}
async function submitAttachObj() {{
  const checkedIds = new Set(
    Array.from(document.querySelectorAll("#aoGrid input:checked"))
      .map(c => parseInt(c.value))
  );
  const toAttach = [...checkedIds].filter(id => !ATTACHED_OBJ_IDS.has(id));
  const toDetach = [...ATTACHED_OBJ_IDS].filter(id => !checkedIds.has(id));
  if (toAttach.length === 0 && toDetach.length === 0) {{
    showToast("Ничего не изменилось"); closeAttachObj(); return;
  }}
  try {{
    const r = await fetch("/api/set_worker_objects", {{
      method:"POST", headers:{{"Content-Type":"application/json"}},
      body: JSON.stringify({{worker_id: WORKER_ID, attach: toAttach, detach: toDetach}})
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast(`Прикреплено ${{d.attached}}, откреплено ${{d.detached}}`);
      closeAttachObj();
      setTimeout(()=>location.reload(), 500);
    }} else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

function openAddShift() {{
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  document.getElementById("asDate").value = `${{yyyy}}-${{mm}}-${{dd}}`;
  document.getElementById("modalAddShift").classList.add("show");
}}
function closeAddShift() {{ document.getElementById("modalAddShift").classList.remove("show"); }}
async function submitAddShift() {{
  const date = document.getElementById("asDate").value;
  const arr = document.getElementById("asArr").value;
  const left = document.getElementById("asLeft").value;
  if (!date) {{ showToast("Укажи дату", true); return; }}
  if (!arr) {{ showToast("Укажи время прихода", true); return; }}
  try {{
    const r = await fetch("/api/backdate_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{date, arrived: arr, left, worker_ids: [WORKER_ID]}}),
    }});
    const data = await r.json();
    if (data.ok && data.ok_count > 0) {{
      showToast("Смена создана");
      closeAddShift();
      setTimeout(() => location.reload(), 500);
    }} else if (data.ok && data.skip_count > 0) {{
      showToast(data.errors[0] || "Не создано", true);
    }} else {{
      showToast(data.error || "Ошибка", true);
    }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

let editingShiftIdPF = null;
function editShiftFromProfile(id, arr, left, name, date) {{
  editingShiftIdPF = id;
  document.getElementById("editTitlePF").textContent = `${{name}} · ${{date}}`;
  document.getElementById("editArrPF").value = arr === "—" ? "" : arr;
  document.getElementById("editLeftPF").value = left === "—" ? "" : left;
  const isClosed = left && left !== "—" && left !== "";
  document.getElementById("editReopenBoxPF").style.display = isClosed ? "block" : "none";
  document.getElementById("modalEditShiftPF").classList.add("show");
}}
function closeEditPF() {{ document.getElementById("modalEditShiftPF").classList.remove("show"); }}
async function submitEditPF() {{
  const arr = document.getElementById("editArrPF").value;
  const left = document.getElementById("editLeftPF").value;
  try {{
    const r = await fetch("/api/edit_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: editingShiftIdPF, arrived: arr, left}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast("Сохранено");
      closeEditPF();
      setTimeout(() => location.reload(), 400);
    }} else {{ showToast(data.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
async function reopenShiftPF() {{
  if (!confirm("Сделать смену снова открытой? Уход будет стёрт.")) return;
  try {{
    const r = await fetch("/api/reopen_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: editingShiftIdPF}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast("Смена снова открыта");
      closeEditPF();
      setTimeout(() => location.reload(), 400);
    }} else {{ showToast(data.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
async function deleteShiftPF() {{
  if (!confirm("Удалить эту смену?")) return;
  try {{
    const r = await fetch("/api/delete_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: editingShiftIdPF}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast("Удалено");
      closeEditPF();
      setTimeout(() => location.reload(), 400);
    }} else {{ showToast(data.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
</script>

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


def render_worker_profile(worker_id: int, user: str) -> str | None:
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
    by_month: dict[str, float] = {}

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
        left_time_for_js = ""
        if s["left_at"]:
            left_dt = dt.datetime.fromisoformat(s["left_at"])
            left_str = left_dt.strftime("%H:%M")
            left_time_for_js = left_str
        pills = []
        if s["auto_closed"]:
            pills.append('<span class="pill auto">авто</span>')
        if not s["left_at"]:
            pills.append('<span class="pill open">открыта</span>')
        late_cls, late_lbl = lateness(s)
        if late_cls and s["left_at"]:
            pills.append(f'<span class="pill {late_cls}">{late_lbl}</span>')
        is_auto = bool(s["auto_closed"])
        is_open = s["left_at"] is None
        cls = "auto" if is_auto else ("open" if is_open else "")
        name_js = html.escape(json.dumps(worker['name'], ensure_ascii=False), quote=True)
        date_js = html.escape(json.dumps(arr.strftime('%d.%m.%Y')), quote=True)
        click_handler = (
            f"editShiftFromProfile({s['id']},"
            f"'{arr.strftime('%H:%M')}',"
            f"'{left_time_for_js}',"
            f"{name_js},{date_js})"
        )
        edit_btn = (
            f'<button class="btn btn-sm" style="padding:3px 10px; font-size:12px;" '
            f'onclick="event.stopPropagation(); {click_handler}">✏️ Изменить</button>'
        )
        rows.append(
            f'<tr class="hover-row {cls}" onclick="{click_handler}">'
            f'<td>{arr.strftime("%d.%m.%Y")}</td>'
            f'<td>{arr.strftime("%H:%M")}</td>'
            f'<td>{left_str}</td>'
            f'<td>{f"{h:.2f}" if h is not None else "—"}</td>'
            f'<td>{" ".join(pills)}</td>'
            f'<td>{edit_btn}</td>'
            f'</tr>'
        )

    by_month_sorted = sorted(by_month.items())
    bm_labels = [k for k, _ in by_month_sorted]
    bm_data = [round(v, 1) for _, v in by_month_sorted]

    is_deleted = worker["deleted_at"] is not None
    status_pill = ('<span class="pill very-late">удалён</span>' if is_deleted else '')
    name_html = html.escape(worker["name"])
    if is_deleted:
        name_html = f'<span style="text-decoration:line-through; color:var(--muted);">{name_html}</span>'

    attached_objects = get_objects_of_worker(worker_id, include_deleted=False)
    attached_obj_ids = [o["id"] for o in attached_objects]
    all_objects = get_objects(include_deleted=False)
    objects_data = [{"id": o["id"], "name": o["name"]} for o in all_objects]

    if attached_objects:
        pills_html = " ".join(
            f'<a href="/object?id={o["id"]}" class="pill" '
            f'style="background:rgba(255, 214, 10, 0.15); color:var(--brand); '
            f'text-decoration:none; padding:4px 12px;">📍 {html.escape(o["name"])}</a>'
            for o in attached_objects
        )
    else:
        pills_html = (
            '<span style="color:var(--muted); font-size:13px;">'
            'Не прикреплён ни к одному объекту</span>'
        )

    return _WORKER_PAGE.format(
        css=COMMON_CSS,
        topbar=topbar("workers", user),
        name=html.escape(worker["name"]),
        name_html=name_html,
        schedule=f"{worker['default_start']}-{worker['default_end']}",
        status_pill=status_pill,
        worker_id=worker["id"],
        default_start=worker["default_start"],
        default_end=worker["default_end"],
        total_hours=f"{total_hours:.1f}",
        this_month_h=f"{this_month_hours:.1f}",
        avg_per_day=f"{avg_per_day:.1f}",
        late_count=late_count,
        overtime_count=overtime_count,
        attached_count=len(attached_objects),
        attached_objects_pills=pills_html,
        objects_json=json.dumps(objects_data, ensure_ascii=False),
        attached_obj_ids=json.dumps(attached_obj_ids),
        heatmap="\n".join(heatmap_cells),
        rows="\n".join(rows) if rows else
            '<tr><td colspan="6" style="text-align:center;color:var(--muted);">Нет смен</td></tr>',
        by_month_labels=json.dumps(bm_labels),
        by_month_data=json.dumps(bm_data),
        total_shifts=len(all_shifts),
    )
