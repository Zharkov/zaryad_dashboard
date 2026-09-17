import html
import json

from views.common import topbar
from db.crews import get_crew_by_id, get_crew_workers
from db.workers import get_workers

_CREW_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · {name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css?v=13">
</head><body>
{topbar}
<div class="container">
<a href="/crews" class="text-sm-muted">← Бригады</a>
<h1>🧩 {name_html}</h1>
{note_html}

<div class="actions">
  <button class="btn btn-primary" onclick="openMembers()">👥 Состав бригады</button>
  <button class="btn btn-danger" onclick="deleteCrew()">🗑 Удалить бригаду</button>
</div>

<div class="scroll-x">
<table>
  <thead><tr><th>Сотрудник</th><th>График</th><th>В бригаде с</th><th>Действия</th></tr></thead>
  <tbody>{member_rows}</tbody>
</table>
</div>

<div class="footer">👥 Участников: {member_count}</div>
</div>

<div class="modal-bg" id="modalMembers" onclick="if(event.target===this)closeMembers()">
  <div class="modal">
    <h3>👥 Состав бригады «{name}»</h3>
    <p class="text-sm-muted">
      Отмеченные уже в бригаде. Сними галку — уберёшь, поставь — добавишь. Нажми «Сохранить».
    </p>
    <div class="search-row">
      <input class="search" id="memSearch" type="text" placeholder="🔍 Поиск..." oninput="memFilter()">
      <button class="btn btn-sm" type="button" onclick="memToggleAll()">Все</button>
    </div>
    <div class="workers-grid" id="memGrid"></div>
    <div class="hint" id="memCount">Выбрано: 0</div>
    <div class="footer-btns">
      <button class="btn" onclick="closeMembers()">Отмена</button>
      <button class="btn btn-primary" onclick="submitMembers()">Сохранить</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const CREW_ID = {crew_id};
const ALL_WORKERS = {workers_json};
const MEMBER_IDS = new Set({member_ids});

function openMembers() {{
  document.getElementById("memSearch").value = "";
  memRender();
  document.getElementById("modalMembers").classList.add("show");
}}
function closeMembers() {{ document.getElementById("modalMembers").classList.remove("show"); }}

function memRender() {{
  const grid = document.getElementById("memGrid");
  const search = (document.getElementById("memSearch").value || "").toLowerCase();
  const currentState = new Map();
  grid.querySelectorAll("input[type=checkbox]").forEach(cb => {{
    currentState.set(parseInt(cb.value), cb.checked);
  }});
  grid.innerHTML = "";
  ALL_WORKERS.filter(w => !search || w.name.toLowerCase().includes(search))
    .forEach(w => {{
      const lbl = document.createElement("label");
      lbl.className = "worker-chk";
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.value = w.id;
      const initial = currentState.has(w.id) ? currentState.get(w.id) : MEMBER_IDS.has(w.id);
      cb.checked = initial;
      cb.addEventListener("change", () => {{
        lbl.classList.toggle("selected", cb.checked);
        memUpdateCount();
      }});
      if (initial) lbl.classList.add("selected");
      const sp = document.createElement("span");
      sp.textContent = w.name;
      lbl.appendChild(cb); lbl.appendChild(sp);
      grid.appendChild(lbl);
    }});
  memUpdateCount();
}}
function memFilter() {{ memRender(); }}
function memToggleAll() {{
  const visible = Array.from(document.querySelectorAll("#memGrid input"));
  const allOn = visible.every(c => c.checked);
  visible.forEach(c => {{ c.checked = !allOn; c.dispatchEvent(new Event("change")); }});
}}
function memUpdateCount() {{
  const n = document.querySelectorAll("#memGrid input:checked").length;
  document.getElementById("memCount").textContent = "Выбрано: " + n;
}}

async function submitMembers() {{
  const checkedIds = new Set(
    Array.from(document.querySelectorAll("#memGrid input:checked")).map(c => parseInt(c.value))
  );
  const toAdd = [...checkedIds].filter(id => !MEMBER_IDS.has(id));
  const toRemove = [...MEMBER_IDS].filter(id => !checkedIds.has(id));
  if (toAdd.length === 0 && toRemove.length === 0) {{
    showToast("Ничего не изменилось");
    closeMembers();
    return;
  }}
  try {{
    const r = await fetch("/api/set_crew_workers", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{crew_id: CREW_ID, add: toAdd, remove: toRemove}})
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast(`Добавлено ${{d.added}}, убрано ${{d.removed}}`);
      closeMembers();
      setTimeout(()=>location.reload(), 500);
    }} else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

async function removeOne(workerId, workerName) {{
  if (!confirm(`Убрать ${{workerName}} из бригады?`)) return;
  try {{
    const r = await fetch("/api/set_crew_workers", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{crew_id: CREW_ID, add: [], remove: [workerId]}})
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Убран"); setTimeout(()=>location.reload(), 400); }}
    else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

async function deleteCrew() {{
  if (!confirm("Удалить бригаду «{name}»? Сотрудники останутся, удалится только сама бригада.")) return;
  try {{
    const r = await fetch("/api/delete_crew", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{id: CREW_ID}})
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Удалена"); setTimeout(()=>location.href="/crews", 500); }}
    else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
</script>
</body></html>
"""


def render_crew_detail(crew_id: int, user: str) -> str | None:
    crew = get_crew_by_id(crew_id)
    if not crew:
        return None

    members = get_crew_workers(crew_id, include_deleted=False)
    member_ids = [w["id"] for w in members]

    all_workers = get_workers(include_deleted=False)
    workers_data = [{"id": w["id"], "name": w["name"]} for w in all_workers]

    note_html = ""
    if crew["note"]:
        note_html = f'<p class="info-block">{html.escape(crew["note"])}</p>'

    member_rows = []
    for w in members:
        name_for_js = html.escape(json.dumps(w["name"], ensure_ascii=False), quote=True)
        member_rows.append(
            f'<tr><td><a href="/worker?id={w["id"]}">{html.escape(w["name"])}</a></td>'
            f'<td>{w["default_start"]}-{w["default_end"]}</td>'
            f'<td class="text-sm-muted">{w["added_at"][:10]}</td>'
            f'<td><button class="btn btn-sm btn-danger" '
            f'onclick="removeOne({w["id"]}, {name_for_js})">Убрать</button></td>'
            f'</tr>'
        )

    return _CREW_PAGE.format(
        topbar=topbar("crews", user),
        name=html.escape(crew["name"]),
        name_html=html.escape(crew["name"]),
        note_html=note_html,
        member_rows="\n".join(member_rows) if member_rows else
            '<tr><td colspan="4" class="empty-cell">'
            'В бригаде пока никого нет. Нажми «👥 Состав бригады»</td></tr>',
        member_count=len(members),
        crew_id=crew_id,
        workers_json=json.dumps(workers_data, ensure_ascii=False),
        member_ids=json.dumps(member_ids),
    )
