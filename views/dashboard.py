import datetime as dt
import html
import json
import urllib.parse

from views.common import topbar
from db.workers import get_workers
from db.shifts import get_shifts, get_open_shifts
from db.comments import get_shift_comments_bulk
from utils import parse_period, now_msk, PERIOD_LABELS, lateness, shift_hours

_DASHBOARD_HTML = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Дашборд</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<link rel="stylesheet" href="/static/style.css">
</head><body>

{topbar}

<div class="container">

<h1>📊 {period_label}</h1>

<div class="actions">
  <button class="btn btn-primary" onclick="openMassMark('arr')">➕ Приход</button>
  <button class="btn btn-primary" onclick="openMassMark('dep')">➖ Уход</button>
  <button class="btn" onclick="openBackdate()">📝 За другой день</button>
  <a class="btn" href="{export_url}">📥 Экспорт CSV</a>
</div>

<div class="periods">{period_links}
  <a href="#" onclick="event.preventDefault(); toggleCal()" class="{custom_active}">📅 Свой период</a>
</div>

<div id="calBlock" class="cal-block" style="{cal_display_style}">
  <form method="GET" action="/" class="flex-row">
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
  <div class="card"><div class="v">{stat_total_hours}</div><div class="l">Часов всего</div></div>
  <div class="card"><div class="v">{stat_workers_count}</div><div class="l">Работников</div></div>
  <div class="card"><div class="v">{stat_shifts_count}</div><div class="l">Смен</div></div>
  <div class="card"><div class="v">{stat_auto_count}</div><div class="l">Автозакрытий</div></div>
  <div class="card"><div class="v">{stat_open_now}</div><div class="l">На работе сейчас</div></div>
</div>

{open_shifts_block}

<h2>Часы по работникам</h2>
<div class="chart-box"><canvas id="byWorker"></canvas></div>

<h2>Тренд по дням</h2>
<div class="chart-box"><canvas id="byDay"></canvas></div>

<h2>Детализация · клик по строке для правки</h2>
<form method="GET" action="/" class="mb-sm">
  <input type="hidden" name="period" value="{period}">
  <input class="search" type="text" name="search" placeholder="🔍 Поиск по имени работника..."
         value="{search_value}" oninput="this.form.submit()">
</form>
<div class="scroll-x">
<table>
  <thead><tr><th>Дата</th><th>Работник</th><th>Приход</th><th>Уход</th><th>Часы</th><th>Пометка</th><th></th></tr></thead>
  <tbody>
{table_rows}
  </tbody>
</table>
</div>

<div class="table-footer" style="display:{totals_display};">
  {totals_row}
</div>

<div class="footer">Обновлено: {now} · автообновление каждые 30 сек</div>

</div>

<div class="modal-bg" id="modalMass" onclick="if(event.target===this)closeMass()">
  <div class="modal">
    <h3 id="massTitle">Массовая отметка</h3>
    <div class="row">
      <label>Время:</label>
      <input type="time" id="massTime">
      <div class="time-presets">
        <button type="button" onclick="setTime('09:00')">9:00</button>
        <button type="button" onclick="setTime('17:00')">17:00</button>
        <button type="button" onclick="setTimeNow()">Сейчас</button>
      </div>
    </div>
    <div class="search-row">
      <input class="search" id="massSearch" type="text" placeholder="🔍 Поиск..."
             oninput="filterWorkers()">
      <button class="btn btn-sm" type="button" onclick="toggleAll()">Все</button>
    </div>
    <div class="workers-grid" id="workersGrid"></div>
    <div class="hint" id="selCount">Выбрано: 0</div>
    <div class="footer-btns">
      <button class="btn" onclick="closeMass()">Отмена</button>
      <button class="btn btn-primary" onclick="submitMass()">Отметить</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalEdit" onclick="if(event.target===this)closeEdit()">
  <div class="modal narrow">
    <h3 id="editTitle">Редактирование смены</h3>
    <div class="row">
      <label class="label-w">Приход:</label>
      <input type="time" id="editArr">
    </div>
    <div class="row">
      <label class="label-w">Уход:</label>
      <input type="time" id="editLeft">
    </div>
    <div class="hint">
      Оставь поле пустым чтобы не менять
    </div>
    <div id="editReopenBox" class="reopen-box">
      <div class="modal-note">
        Сделать смену снова открытой? Уход будет стёрт, работник станет «на работе».
      </div>
      <button class="btn btn-sm btn-primary" onclick="reopenShift()">
        🕘 Снова открыть смену
      </button>
    </div>
    <hr style="border:none; border-top:1px solid var(--border); margin:14px 0 10px;">
    <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--muted); margin-bottom:8px;">💬 Комментарии к смене</div>
    <div id="editShiftComments"></div>
    <textarea id="editShiftCommentText" class="textarea-full mt-sm mb-sm" rows="2"
              placeholder="Добавить комментарий..."></textarea>
    <div class="mb-sm">
      <button class="btn btn-sm btn-primary" onclick="submitShiftComment()">💬 Добавить</button>
    </div>
    <div class="footer-btns">
      <button class="btn btn-danger" onclick="deleteShift()">🗑 Удалить</button>
      <button class="btn" onclick="closeEdit()">Отмена</button>
      <button class="btn btn-primary" onclick="submitEdit()">Сохранить</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalBackdate" onclick="if(event.target===this)closeBackdate()">
  <div class="modal">
    <h3>📝 Смена за другой день</h3>
    <div class="row flex-wrap">
      <div>
        <label class="field-label">Дата:</label>
        <input type="date" id="bdDate">
      </div>
      <div>
        <label class="field-label">Приход:</label>
        <input type="time" id="bdArr">
      </div>
      <div>
        <label class="field-label">Уход (можно пусто):</label>
        <input type="time" id="bdLeft">
      </div>
    </div>
    <div class="time-presets mt-sm">
      <button type="button" onclick="bdSetUsual()">⚡ Как обычно (по графику)</button>
    </div>
    <div class="search-row">
      <input class="search" id="bdSearch" type="text" placeholder="🔍 Поиск работников..."
             oninput="bdFilterWorkers()">
      <button class="btn btn-sm" type="button" onclick="bdToggleAll()">Все</button>
    </div>
    <div class="workers-grid" id="bdWorkersGrid"></div>
    <div class="hint" id="bdSelCount">Выбрано: 0</div>
    <div class="hint-warn">
      ⚠ Если у работника уже есть запись на эту дату — она будет пропущена.
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeBackdate()">Отмена</button>
      <button class="btn btn-primary" onclick="submitBackdate()">Создать смены</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const WORKERS = {workers_json};
let massAction = "arr";
let editingShiftId = null;

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}}

const chartOpts = {{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {{ legend: {{ labels: {{ color: "#c9d1d9" }} }} }},
  scales: {{
    x: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#30363d" }} }},
    y: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#30363d" }}, beginAtZero: true }}
  }}
}};
new Chart(document.getElementById("byWorker"), {{
  type: "bar",
  data: {{ labels: {chart_by_worker_labels}, datasets: [{{
    label: "Часов", data: {chart_by_worker_data},
    backgroundColor: "#ffd60a", borderRadius: 4
  }}] }},
  options: {{ ...chartOpts, indexAxis: "y" }}
}});
new Chart(document.getElementById("byDay"), {{
  type: "line",
  data: {{ labels: {chart_by_day_labels}, datasets: [{{
    label: "Часов в день", data: {chart_by_day_data},
    borderColor: "#ffd60a", backgroundColor: "rgba(255, 214, 10, 0.15)",
    fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: "#ffd60a"
  }}] }},
  options: chartOpts
}});

function openBackdate() {{
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  document.getElementById("bdDate").value = `${{yyyy}}-${{mm}}-${{dd}}`;
  document.getElementById("bdArr").value = "09:00";
  document.getElementById("bdLeft").value = "17:00";
  document.getElementById("bdSearch").value = "";
  bdRenderWorkers([]);
  bdUpdateCount();
  document.getElementById("modalBackdate").classList.add("show");
}}
function closeBackdate() {{ document.getElementById("modalBackdate").classList.remove("show"); }}
function bdRenderWorkers(filterIds) {{
  const grid = document.getElementById("bdWorkersGrid");
  const search = (document.getElementById("bdSearch").value || "").toLowerCase();
  grid.innerHTML = "";
  WORKERS.filter(w => !search || w.name.toLowerCase().includes(search))
    .forEach(w => {{
      const lbl = document.createElement("label");
      lbl.className = "worker-chk";
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.value = w.id;
      cb.dataset.ds = w.ds; cb.dataset.de = w.de;
      cb.checked = filterIds.includes(w.id);
      cb.addEventListener("change", () => {{
        lbl.classList.toggle("selected", cb.checked);
        bdUpdateCount();
      }});
      if (cb.checked) lbl.classList.add("selected");
      const sp = document.createElement("span");
      sp.textContent = w.name;
      const sched = document.createElement("span");
      sched.style.color = "var(--muted)"; sched.style.fontSize = "11px";
      sched.style.marginLeft = "auto";
      sched.textContent = w.ds + "-" + w.de;
      lbl.appendChild(cb); lbl.appendChild(sp); lbl.appendChild(sched);
      grid.appendChild(lbl);
    }});
}}
function bdFilterWorkers() {{
  const checked = Array.from(document.querySelectorAll("#bdWorkersGrid input:checked"))
    .map(c => parseInt(c.value));
  bdRenderWorkers(checked);
}}
function bdToggleAll() {{
  const visible = Array.from(document.querySelectorAll("#bdWorkersGrid input"));
  const allOn = visible.every(c => c.checked);
  visible.forEach(c => {{ c.checked = !allOn; c.dispatchEvent(new Event("change")); }});
}}
function bdUpdateCount() {{
  const n = document.querySelectorAll("#bdWorkersGrid input:checked").length;
  document.getElementById("bdSelCount").textContent = "Выбрано: " + n;
}}
function bdSetUsual() {{
  const checked = Array.from(document.querySelectorAll("#bdWorkersGrid input:checked"));
  if (!checked.length) {{
    document.getElementById("bdArr").value = "09:00";
    document.getElementById("bdLeft").value = "17:00";
    return;
  }}
  const dsSet = new Set(checked.map(c => c.dataset.ds));
  const deSet = new Set(checked.map(c => c.dataset.de));
  if (dsSet.size === 1) document.getElementById("bdArr").value = checked[0].dataset.ds;
  if (deSet.size === 1) document.getElementById("bdLeft").value = checked[0].dataset.de;
  if (dsSet.size > 1 || deSet.size > 1) {{
    showToast("У выбранных разные графики, поставлено по первому", false);
  }}
}}
async function submitBackdate() {{
  const date = document.getElementById("bdDate").value;
  const arr = document.getElementById("bdArr").value;
  const left = document.getElementById("bdLeft").value;
  const ids = Array.from(document.querySelectorAll("#bdWorkersGrid input:checked"))
    .map(c => parseInt(c.value));
  if (!date) {{ showToast("Укажи дату", true); return; }}
  if (!arr) {{ showToast("Укажи время прихода", true); return; }}
  if (!ids.length) {{ showToast("Выбери работников", true); return; }}
  try {{
    const r = await fetch("/api/backdate_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{date, arrived: arr, left, worker_ids: ids}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast(`Создано ${{data.ok_count}} · пропущено ${{data.skip_count}}`);
      closeBackdate();
      setTimeout(() => location.reload(), 600);
    }} else {{
      showToast(data.error || "Ошибка", true);
    }}
  }} catch (e) {{
    showToast("Сеть: " + e.message, true);
  }}
}}

function toggleCal() {{
  const b = document.getElementById("calBlock");
  b.style.display = (b.style.display === "none" || !b.style.display) ? "block" : "none";
}}

async function closeShiftNow(shiftId, workerName) {{
  if (!confirm(`Закрыть смену ${{workerName}} текущим временем?`)) return;
  try {{
    const r = await fetch("/api/close_shift_now", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: shiftId}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast(`✅ ${{workerName}} — уход ${{data.time}}`);
      setTimeout(() => location.reload(), 500);
    }} else {{
      showToast(data.error || "Ошибка", true);
    }}
  }} catch (e) {{
    showToast("Сеть: " + e.message, true);
  }}
}}

function openMassMark(action) {{
  massAction = action;
  document.getElementById("massTitle").textContent =
    action === "arr" ? "➕ Массовая отметка прихода" : "➖ Массовая отметка ухода";
  document.getElementById("massTime").value = "";
  document.getElementById("massSearch").value = "";
  renderWorkers([]);
  updateCount();
  document.getElementById("modalMass").classList.add("show");
}}
function closeMass() {{ document.getElementById("modalMass").classList.remove("show"); }}
function setTime(t) {{ document.getElementById("massTime").value = t; }}
function setTimeNow() {{
  const d = new Date();
  setTime(String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0"));
}}
function renderWorkers(filterIds) {{
  const grid = document.getElementById("workersGrid");
  const search = (document.getElementById("massSearch").value || "").toLowerCase();
  grid.innerHTML = "";
  WORKERS.filter(w => !search || w.name.toLowerCase().includes(search))
    .forEach(w => {{
      const lbl = document.createElement("label");
      lbl.className = "worker-chk";
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.value = w.id; cb.dataset.ds = w.ds; cb.dataset.de = w.de;
      cb.checked = filterIds.includes(w.id);
      cb.addEventListener("change", () => {{
        lbl.classList.toggle("selected", cb.checked);
        updateCount();
      }});
      if (cb.checked) lbl.classList.add("selected");
      const sp = document.createElement("span");
      sp.textContent = w.name;
      const sched = document.createElement("span");
      sched.style.color = "var(--muted)"; sched.style.fontSize = "11px";
      sched.style.marginLeft = "auto";
      sched.textContent = w.ds + "-" + w.de;
      lbl.appendChild(cb); lbl.appendChild(sp); lbl.appendChild(sched);
      grid.appendChild(lbl);
    }});
}}
function filterWorkers() {{
  const checked = Array.from(document.querySelectorAll("#workersGrid input:checked"))
    .map(c => parseInt(c.value));
  renderWorkers(checked);
}}
function toggleAll() {{
  const visible = Array.from(document.querySelectorAll("#workersGrid input"));
  const allOn = visible.every(c => c.checked);
  visible.forEach(c => {{
    c.checked = !allOn;
    c.dispatchEvent(new Event("change"));
  }});
}}
function updateCount() {{
  const n = document.querySelectorAll("#workersGrid input:checked").length;
  document.getElementById("selCount").textContent = "Выбрано: " + n;
}}
async function submitMass() {{
  const time = document.getElementById("massTime").value;
  if (!time) {{ showToast("Укажи время", true); return; }}
  const ids = Array.from(document.querySelectorAll("#workersGrid input:checked"))
    .map(c => parseInt(c.value));
  if (!ids.length) {{ showToast("Выбери работников", true); return; }}
  try {{
    const r = await fetch("/api/mass_mark", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{action: massAction, time, worker_ids: ids}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast(`Готово · OK ${{data.ok_count}} · ошибок ${{data.err_count}}`);
      closeMass();
      setTimeout(() => location.reload(), 600);
    }} else {{
      showToast(data.error || "Ошибка", true);
    }}
  }} catch (e) {{
    showToast("Сеть: " + e.message, true);
  }}
}}

function editShift(id, arr, left, name, date) {{
  editingShiftId = id;
  document.getElementById("editTitle").textContent = `${{name}} · ${{date}}`;
  document.getElementById("editArr").value = arr === "—" ? "" : arr;
  document.getElementById("editLeft").value = left === "—" ? "" : left;
  const isClosed = left && left !== "—";
  document.getElementById("editReopenBox").style.display = isClosed ? "block" : "none";
  document.getElementById("editShiftCommentText").value = "";
  document.getElementById("modalEdit").classList.add("show");
  loadShiftComments(id);
}}

async function loadShiftComments(shiftId) {{
  const box = document.getElementById("editShiftComments");
  box.innerHTML = '<div class="text-sm-muted" style="padding:4px 0">Загрузка...</div>';
  try {{
    const r = await fetch("/api/shift_comments?shift_id=" + shiftId);
    const d = await r.json();
    if (d.ok) renderShiftComments(d.comments);
    else box.innerHTML = '<div class="text-sm-muted">Ошибка загрузки</div>';
  }} catch(e) {{
    box.innerHTML = '<div class="text-sm-muted">Ошибка сети</div>';
  }}
}}
function renderShiftComments(comments) {{
  const box = document.getElementById("editShiftComments");
  if (!comments.length) {{
    box.innerHTML = '<div class="text-sm-muted" style="padding:4px 0">Комментариев пока нет</div>';
    return;
  }}
  box.innerHTML = comments.map(c => {{
    const dt = new Date(c.created_at);
    const ds = dt.toLocaleString("ru-RU", {{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"}});
    return '<div class="comment-card">' +
      '<div class="comment-meta">' +
      '<span class="comment-author">👤 ' + escHtml(c.author) + '</span>' +
      '<span class="comment-date">' + ds + '</span>' +
      '<button class="btn btn-sm btn-danger" onclick="deleteShiftComment(' + c.id + ')">× Удалить</button>' +
      '</div>' +
      '<div class="comment-body">' + escHtml(c.text) + '</div>' +
      '</div>';
  }}).join("");
}}
function escHtml(s) {{
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}}
async function submitShiftComment() {{
  const text = document.getElementById("editShiftCommentText").value.trim();
  if (!text) {{ showToast("Введи текст", true); return; }}
  try {{
    const r = await fetch("/api/add_shift_comment", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{shift_id: editingShiftId, text}}),
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast("Добавлено");
      setTimeout(() => location.reload(), 400);
    }} else showToast(d.error || "Ошибка", true);
  }} catch(e) {{ showToast("Сеть: " + e.message, true); }}
}}
async function deleteShiftComment(id) {{
  if (!confirm("Удалить комментарий?")) return;
  try {{
    const r = await fetch("/api/delete_shift_comment", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Удалено"); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || "Ошибка", true);
  }} catch(e) {{ showToast("Сеть: " + e.message, true); }}
}}
function closeEdit() {{ document.getElementById("modalEdit").classList.remove("show"); }}
async function submitEdit() {{
  const arr = document.getElementById("editArr").value;
  const left = document.getElementById("editLeft").value;
  try {{
    const r = await fetch("/api/edit_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: editingShiftId, arrived: arr, left}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast("Сохранено");
      closeEdit();
      setTimeout(() => location.reload(), 400);
    }} else {{
      showToast(data.error || "Ошибка", true);
    }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
async function reopenShift() {{
  if (!confirm("Сделать смену снова открытой? Уход будет стёрт.")) return;
  try {{
    const r = await fetch("/api/reopen_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: editingShiftId}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast("Смена снова открыта");
      closeEdit();
      setTimeout(() => location.reload(), 400);
    }} else {{ showToast(data.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
async function deleteShift() {{
  if (!confirm("Удалить эту смену?")) return;
  try {{
    const r = await fetch("/api/delete_shift", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{id: editingShiftId}}),
    }});
    const data = await r.json();
    if (data.ok) {{
      showToast("Удалено");
      closeEdit();
      setTimeout(() => location.reload(), 400);
    }} else {{ showToast(data.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

setInterval(() => {{
  if (document.querySelector(".modal-bg.show")) return;
  location.reload();
}}, 30000);
</script>
</body></html>
"""


def render_dashboard(period: str, search: str, user: str,
                     custom_from: str = "", custom_to: str = "") -> str:
    date_from, date_to = parse_period(period, custom_from, custom_to)
    shifts = get_shifts(date_from, date_to)
    workers = get_workers(include_deleted=False)

    search_low = search.lower().strip()
    if search_low:
        shifts = [s for s in shifts if search_low in s["worker_name"].lower()]

    now = now_msk()
    shift_comments_map = get_shift_comments_bulk([s["id"] for s in shifts])
    rows = []
    total_hours = 0.0
    open_running_hours = 0.0
    auto_count = 0
    workers_with_data = set()

    for s in shifts:
        arr = dt.datetime.fromisoformat(s["arrived_at"])
        h = shift_hours(s)
        is_auto = bool(s["auto_closed"])
        is_open = s["left_at"] is None

        if h is not None:
            total_hours += h
            workers_with_data.add(s["worker_name"])
            if is_auto:
                auto_count += 1
        if is_open:
            delta_sec = (now - arr).total_seconds()
            if delta_sec > 0:
                open_running_hours += delta_sec / 3600

        left_str = "—"
        hours_str = "—"
        if s["left_at"]:
            left = dt.datetime.fromisoformat(s["left_at"])
            left_str = left.strftime("%H:%M")
            hours_str = f"{h:.2f}"
        elif is_open:
            delta = now - arr
            hrs = int(delta.total_seconds() // 3600)
            mins = int((delta.total_seconds() % 3600) // 60)
            hours_str = f'<span class="text-brand">{hrs}ч {mins:02d}мин</span>'
            if arr.date() == now.date():
                left_str = (
                    f'<button class="btn btn-sm" '
                    f'onclick="event.stopPropagation(); closeShiftNow({s["id"]}, '
                    f'{json.dumps(s["worker_name"])});">'
                    f'🕘 Закрыть сейчас</button>'
                )

        cls = "auto" if is_auto else ("open" if is_open else "")

        pills = []
        if is_auto:
            pills.append('<span class="pill auto">авто</span>')
        if is_open:
            pills.append('<span class="pill open">открыта</span>')
        late_cls, late_lbl = lateness(s)
        if late_cls and not is_open:
            pills.append(f'<span class="pill {late_cls}">{late_lbl}</span>')
        s_comments = shift_comments_map.get(s["id"], [])
        if s_comments:
            pills.append(f'<span class="pill" title="Комментариев: {len(s_comments)}">💬 {len(s_comments)}</span>')
        pill_html = " ".join(pills)

        worker_link = (
            f'<a href="/worker?id={s["worker_id"]}" onclick="event.stopPropagation();" '
            f'title="Открыть профиль" '
            f'class="worker-link">👤</a>'
            f'<span>{html.escape(s["worker_name"])}</span>'
        )

        name_js = html.escape(json.dumps(s["worker_name"], ensure_ascii=False), quote=True)
        date_js = html.escape(json.dumps(arr.strftime("%d.%m.%Y")), quote=True)
        arr_hhmm = arr.strftime('%H:%M')
        left_hhmm = dt.datetime.fromisoformat(s['left_at']).strftime('%H:%M') if s['left_at'] else ''
        click_call = f"editShift({s['id']},'{arr_hhmm}','{left_hhmm}',{name_js},{date_js})"
        edit_btn = (
            f'<button class="btn btn-sm" '
            f'onclick="event.stopPropagation(); {click_call}">✏️</button>'
        )
        rows.append(
            f'<tr class="hover-row {cls}" onclick="{click_call}">'
            f'<td>{arr.strftime("%d.%m")}</td>'
            f'<td>{worker_link}</td>'
            f'<td>{arr.strftime("%H:%M")}</td>'
            f'<td>{left_str}</td>'
            f'<td>{hours_str}</td>'
            f'<td>{pill_html}</td>'
            f'<td>{edit_btn}</td>'
            f'</tr>'
        )
        if s_comments:
            comment_cards = []
            for c in s_comments:
                created = dt.datetime.fromisoformat(c["created_at"])
                comment_cards.append(
                    f'<div class="comment-card" style="margin:4px 0;">'
                    f'<div class="comment-meta">'
                    f'<span class="comment-author">👤 {html.escape(c["author"])}</span>'
                    f'<span class="comment-date">{created.strftime("%d.%m %H:%M")}</span>'
                    f'<button class="btn btn-sm btn-danger" '
                    f'onclick="event.stopPropagation(); deleteShiftComment({c["id"]})">'
                    f'× Удалить</button>'
                    f'</div>'
                    f'<div class="comment-body">{html.escape(c["text"])}</div>'
                    f'</div>'
                )
            rows.append(
                f'<tr onclick="event.stopPropagation()" style="cursor:default;">'
                f'<td colspan="7" style="padding:0 12px 8px; border-top:none; '
                f'background:rgba(255,214,10,0.02);">'
                + "".join(comment_cards) +
                f'</td></tr>'
            )

    filter_active = bool(search_low)
    totals_str = ""
    if shifts:
        totals_parts = [
            f"<strong>Смен:</strong> {len(shifts)}",
            f"<strong>Часов закрытых:</strong> {total_hours:.1f}",
        ]
        if open_running_hours > 0:
            totals_parts.append(
                f'<strong>+ открытых:</strong> '
                f'<span class="text-brand">{open_running_hours:.1f}</span>'
            )
        if auto_count:
            totals_parts.append(f'<strong>Авто:</strong> {auto_count}')
        totals_str = " · ".join(totals_parts)
        if filter_active:
            totals_str = f"🔍 Фильтр «{html.escape(search)}» · " + totals_str

    open_now = get_open_shifts()
    open_html = ""
    if open_now:
        items = []
        for o in open_now:
            arr = dt.datetime.fromisoformat(o["arrived_at"])
            delta = now - arr
            hrs = int(delta.total_seconds() // 3600)
            mins = int((delta.total_seconds() % 3600) // 60)
            items.append(
                f'<li><a href="/worker?id={o["worker_id"]}">'
                f'{html.escape(o["worker_name"])}</a> — с '
                f'{arr.strftime("%H:%M")} ({hrs}ч {mins}мин)</li>'
            )
        open_html = (
            '<div class="open-shifts"><strong>👥 Сейчас на работе:</strong>'
            f'<ul>{"".join(items)}</ul></div>'
        )

    by_worker: dict[str, float] = {}
    for s in shifts:
        h = shift_hours(s)
        if h is None:
            continue
        by_worker[s["worker_name"]] = by_worker.get(s["worker_name"], 0) + h
    by_worker_sorted = sorted(by_worker.items(), key=lambda kv: -kv[1])
    bw_labels = [n for n, _ in by_worker_sorted]
    bw_data = [round(h, 2) for _, h in by_worker_sorted]

    by_day: dict[str, float] = {}
    d = date_from
    while d <= date_to:
        by_day[d.isoformat()] = 0.0
        d += dt.timedelta(days=1)
    for s in shifts:
        h = shift_hours(s)
        if h is None:
            continue
        by_day[s["date"]] = by_day.get(s["date"], 0) + h
    bd_labels = [dt.date.fromisoformat(d).strftime("%d.%m") for d in by_day]
    bd_data = [round(h, 2) for h in by_day.values()]

    workers_data = [
        {"id": w["id"], "name": w["name"],
         "ds": w["default_start"], "de": w["default_end"]}
        for w in workers
    ]

    search_qs = ("&search=" + urllib.parse.quote(search)) if search else ""
    period_links = "".join(
        f'<a href="?period={p}{search_qs}" '
        f'class="{"active" if period == p else ""}">{label}</a>'
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

    export_qs = f"period={period}"
    if period == "custom":
        export_qs += f"&from={custom_from}&to={custom_to}"

    return _DASHBOARD_HTML.format(
        topbar=topbar("dashboard", user),
        period_label=PERIOD_LABELS.get(period, period),
        period=period,
        period_links=period_links,
        custom_active=custom_active,
        cal_from=cal_from,
        cal_to=cal_to,
        cal_display_style=cal_display_style,
        search_value=html.escape(search),
        date_from=date_from.strftime("%d.%m.%Y"),
        date_to=date_to.strftime("%d.%m.%Y"),
        stat_total_hours=f"{total_hours:.1f}",
        stat_workers_count=len(workers_with_data),
        stat_shifts_count=len(shifts),
        stat_auto_count=auto_count,
        stat_open_now=len(open_now),
        open_shifts_block=open_html,
        table_rows="\n".join(rows) if rows else
            '<tr><td colspan="7" class="empty-cell">Нет данных за период</td></tr>',
        totals_row=totals_str,
        totals_display="block" if totals_str else "none",
        chart_by_worker_labels=json.dumps(bw_labels, ensure_ascii=False),
        chart_by_worker_data=json.dumps(bw_data),
        chart_by_day_labels=json.dumps(bd_labels, ensure_ascii=False),
        chart_by_day_data=json.dumps(bd_data),
        workers_json=json.dumps(workers_data, ensure_ascii=False),
        now=now.strftime("%d.%m.%Y %H:%M"),
        export_url=f"/export?{export_qs}",
    )
