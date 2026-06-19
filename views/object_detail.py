import datetime as dt
import html
import json

from views.common import topbar
from db.objects import get_object_by_id
from db.workers import get_workers
from db.attachments import get_workers_of_object
from db.comments import get_object_comments

_OBJECT_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · {name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css?v=7">
</head><body>
{topbar}
<div class="container">
<a href="/objects" class="text-sm-muted">← Объекты</a>
<h1>📍 {name_html}</h1>
{description_html}
<p class="subtitle">{status_pill}</p>

<div class="actions">
  <button class="btn btn-primary" onclick="openAttach()">👥 Прикрепить работников</button>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('workers', this)">👥 Работники ({worker_count})</button>
  <button class="tab-btn" onclick="switchTab('comments', this)">💬 Заметки ({comments_count})</button>
</div>

<div id="tab_workers" class="tab-panel active">
<div class="scroll-x">
<table>
  <thead><tr><th>Имя</th><th>График</th><th>Прикреплён</th><th>Действия</th></tr></thead>
  <tbody>{worker_rows}</tbody>
</table>
</div>
</div>

<div id="tab_comments" class="tab-panel">
  <div id="commentsBlock">{comments_html}</div>
  <div class="mt-sm">
    <textarea id="commentText" class="textarea-full mb-sm" rows="3"
              placeholder="Написать заметку к объекту..."></textarea>
    <button class="btn btn-primary" onclick="submitComment()">💬 Добавить</button>
  </div>
</div>

<div class="footer">📍 {name}</div>
</div>

<div class="modal-bg" id="modalAttach" onclick="if(event.target===this)closeAttach()">
  <div class="modal">
    <h3>👥 Прикрепить работников к "{name}"</h3>
    <p class="text-sm-muted">
      Уже прикреплённые показаны отмеченными. Снять галку — открепить, поставить — прикрепить.
      Нажми «Сохранить» чтобы применить.
    </p>
    <div class="search-row">
      <input class="search" id="attSearch" type="text" placeholder="🔍 Поиск..."
             oninput="attFilter()">
      <button class="btn btn-sm" type="button" onclick="attToggleAll()">Все</button>
    </div>
    <div class="workers-grid" id="attGrid"></div>
    <div class="hint" id="attCount">Выбрано: 0</div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAttach()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAttach()">Сохранить</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const OBJECT_ID = {object_id};
const ALL_WORKERS = {workers_json};
const ATTACHED_IDS = new Set({attached_ids});

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}}

function openAttach() {{
  document.getElementById("attSearch").value = "";
  attRender();
  document.getElementById("modalAttach").classList.add("show");
}}
function closeAttach() {{ document.getElementById("modalAttach").classList.remove("show"); }}

function attRender() {{
  const grid = document.getElementById("attGrid");
  const search = (document.getElementById("attSearch").value || "").toLowerCase();
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
      const initial = currentState.has(w.id) ? currentState.get(w.id) : ATTACHED_IDS.has(w.id);
      cb.checked = initial;
      cb.addEventListener("change", () => {{
        lbl.classList.toggle("selected", cb.checked);
        attUpdateCount();
      }});
      if (initial) lbl.classList.add("selected");
      const sp = document.createElement("span");
      sp.textContent = w.name;
      lbl.appendChild(cb); lbl.appendChild(sp);
      grid.appendChild(lbl);
    }});
  attUpdateCount();
}}
function attFilter() {{ attRender(); }}
function attToggleAll() {{
  const visible = Array.from(document.querySelectorAll("#attGrid input"));
  const allOn = visible.every(c => c.checked);
  visible.forEach(c => {{ c.checked = !allOn; c.dispatchEvent(new Event("change")); }});
}}
function attUpdateCount() {{
  const n = document.querySelectorAll("#attGrid input:checked").length;
  document.getElementById("attCount").textContent = "Выбрано: " + n;
}}

async function submitAttach() {{
  const checkedIds = new Set(
    Array.from(document.querySelectorAll("#attGrid input:checked"))
      .map(c => parseInt(c.value))
  );
  const toAttach = [...checkedIds].filter(id => !ATTACHED_IDS.has(id));
  const toDetach = [...ATTACHED_IDS].filter(id => !checkedIds.has(id));
  if (toAttach.length === 0 && toDetach.length === 0) {{
    showToast("Ничего не изменилось");
    closeAttach();
    return;
  }}
  try {{
    const r = await fetch("/api/set_object_workers", {{
      method:"POST", headers:{{"Content-Type":"application/json"}},
      body: JSON.stringify({{object_id: OBJECT_ID, attach: toAttach, detach: toDetach}})
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast(`Прикреплено ${{d.attached}}, откреплено ${{d.detached}}`);
      closeAttach();
      setTimeout(()=>location.reload(), 500);
    }} else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

function switchTab(name, btn) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab_' + name).classList.add('active');
}}

async function submitComment() {{
  const text = document.getElementById('commentText').value.trim();
  if (!text) {{ showToast('Введи текст', true); return; }}
  try {{
    const r = await fetch('/api/add_object_comment', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{object_id: OBJECT_ID, text}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Добавлено'); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}

async function deleteComment(id) {{
  if (!confirm('Удалить заметку?')) return;
  try {{
    const r = await fetch('/api/delete_object_comment', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{id}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Удалено'); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}

async function detachOne(workerId, workerName) {{
  if (!confirm(`Открепить ${{workerName}}?`)) return;
  try {{
    const r = await fetch("/api/detach_worker", {{
      method:"POST", headers:{{"Content-Type":"application/json"}},
      body: JSON.stringify({{worker_id: workerId, object_id: OBJECT_ID}})
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Откреплён"); setTimeout(()=>location.reload(), 400); }}
    else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
</script>
</body></html>
"""


def render_object_detail(object_id: int, user: str) -> str | None:
    obj = get_object_by_id(object_id)
    if not obj:
        return None

    is_deleted = obj["deleted_at"] is not None
    attached = get_workers_of_object(object_id, include_deleted=False)
    attached_ids = [w["id"] for w in attached]
    comments = get_object_comments(object_id)
    if comments:
        cards = []
        for c in comments:
            created = dt.datetime.fromisoformat(c["created_at"])
            cards.append(
                f'<div class="comment-card">'
                f'<div class="comment-meta">'
                f'<span class="comment-author">👤 {html.escape(c["author"])}</span>'
                f'<span class="comment-date">{created.strftime("%d.%m.%Y %H:%M")}</span>'
                f'<button class="btn btn-sm btn-danger" '
                f'onclick="deleteComment({c["id"]})">× Удалить</button>'
                f'</div>'
                f'<div class="comment-body">{html.escape(c["text"])}</div>'
                f'</div>'
            )
        comments_html = "\n".join(cards)
    else:
        comments_html = '<p class="text-sm-muted">Заметок пока нет</p>'

    all_workers = get_workers(include_deleted=False)
    workers_data = [{"id": w["id"], "name": w["name"]} for w in all_workers]

    desc_html = ""
    if obj["description"]:
        desc_html = (
            f'<p class="info-block">'
            f'{html.escape(obj["description"])}</p>'
        )

    status_pill = ('<span class="pill very-late">закрыт</span>' if is_deleted else '')

    name_html_v = html.escape(obj["name"])
    if is_deleted:
        name_html_v = f'<span class="strike">{name_html_v}</span>'

    worker_rows = []
    for w in attached:
        att_dt = dt.datetime.fromisoformat(w["attached_at"])
        att_str = att_dt.strftime("%d.%m.%Y")
        name_for_js = html.escape(json.dumps(w["name"], ensure_ascii=False), quote=True)
        worker_rows.append(
            f'<tr><td><a href="/worker?id={w["id"]}">{html.escape(w["name"])}</a></td>'
            f'<td>{w["default_start"]}-{w["default_end"]}</td>'
            f'<td class="text-sm-muted">{att_str}</td>'
            f'<td><button class="btn btn-sm btn-danger" '
            f'onclick="detachOne({w["id"]}, {name_for_js})">Открепить</button></td>'
            f'</tr>'
        )

    return _OBJECT_PAGE.format(
        topbar=topbar("objects", user),
        name=html.escape(obj["name"]),
        name_html=name_html_v,
        description_html=desc_html,
        status_pill=status_pill,
        worker_count=len(attached),
        worker_rows="\n".join(worker_rows) if worker_rows else
            '<tr><td colspan="4" class="empty-cell">'
            'Никто не прикреплён. Нажми «👥 Прикрепить работников»</td></tr>',
        comments_html=comments_html,
        comments_count=len(comments),
        object_id=object_id,
        workers_json=json.dumps(workers_data, ensure_ascii=False),
        attached_ids=json.dumps(attached_ids),
    )
