import html
import json

from views.common import COMMON_CSS, topbar
from db.objects import get_objects
from db.attachments import count_workers_per_object

_OBJECTS_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Объекты</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style>
</head><body>
{topbar}
<div class="container">
<h1>📍 Объекты</h1>

<div class="actions">
  <button class="btn btn-primary" onclick="openAddObject()">➕ Добавить объект</button>
</div>

<form method="GET" action="/objects" style="margin-bottom:12px;">
  <input class="search" type="text" name="search" placeholder="🔍 Поиск..."
         value="{search_value}" oninput="this.form.submit()">
</form>

<div style="overflow-x:auto;">
<table>
  <thead><tr><th>Название</th><th>Работников</th><th>Описание</th><th>Статус</th><th>Действия</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
</div>

<div class="footer">Всего: {total}</div>

</div>

<div class="modal-bg" id="modalAddO" onclick="if(event.target===this)closeAddO()">
  <div class="modal narrow">
    <h3>➕ Добавить объект</h3>
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Название:</label>
      <input type="text" id="addOName" placeholder="Кашена, Центр, Победы 12..."
             style="width:100%; background:var(--bg); border:1px solid var(--border);
                    border-radius:6px; padding:8px 12px; color:var(--text);
                    font-size:14px; font-family:inherit;">
    </div>
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Описание (опционально):</label>
      <textarea id="addODesc" rows="3" placeholder="Что за объект, кто заказчик и т.п."
                style="width:100%; background:var(--bg); border:1px solid var(--border);
                       border-radius:6px; padding:8px 12px; color:var(--text);
                       font-size:14px; font-family:inherit; resize:vertical;"></textarea>
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAddO()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAddO()">Создать</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalEditO" onclick="if(event.target===this)closeEditO()">
  <div class="modal narrow">
    <h3 id="editOTitle">Редактирование</h3>
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Название:</label>
      <input type="text" id="editOName"
             style="width:100%; background:var(--bg); border:1px solid var(--border);
                    border-radius:6px; padding:8px 12px; color:var(--text);
                    font-size:14px; font-family:inherit;">
    </div>
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Описание:</label>
      <textarea id="editODesc" rows="3"
                style="width:100%; background:var(--bg); border:1px solid var(--border);
                       border-radius:6px; padding:8px 12px; color:var(--text);
                       font-size:14px; font-family:inherit; resize:vertical;"></textarea>
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeEditO()">Отмена</button>
      <button class="btn btn-primary" onclick="submitEditO()">Сохранить</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let editingObjectId = null;

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}}

function openAddObject() {{
  document.getElementById("addOName").value = "";
  document.getElementById("addODesc").value = "";
  document.getElementById("modalAddO").classList.add("show");
  setTimeout(() => document.getElementById("addOName").focus(), 100);
}}
function closeAddO() {{ document.getElementById("modalAddO").classList.remove("show"); }}
async function submitAddO() {{
  const name = document.getElementById("addOName").value.trim();
  const desc = document.getElementById("addODesc").value;
  if (!name) {{ showToast("Введи название", true); return; }}
  try {{
    const r = await fetch("/api/add_object", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{name, description: desc}}),
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast(`✅ Создан: ${{name}}`);
      closeAddO();
      setTimeout(()=>location.reload(), 500);
    }} else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

function openEditObject(id, name, desc) {{
  editingObjectId = id;
  document.getElementById("editOTitle").textContent = `✏️ ${{name}}`;
  document.getElementById("editOName").value = name;
  document.getElementById("editODesc").value = desc || "";
  document.getElementById("modalEditO").classList.add("show");
}}
function closeEditO() {{ document.getElementById("modalEditO").classList.remove("show"); }}
async function submitEditO() {{
  const name = document.getElementById("editOName").value.trim();
  const desc = document.getElementById("editODesc").value;
  if (!name) {{ showToast("Введи название", true); return; }}
  try {{
    const r = await fetch("/api/update_object", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{id: editingObjectId, name, description: desc}}),
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast("✅ Сохранено"); closeEditO();
      setTimeout(()=>location.reload(), 500);
    }} else {{ showToast(d.error || "Ошибка", true); }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

async function delObject(id, name) {{
  if (!confirm(`Удалить объект "${{name}}"? Прикрепления работников сохранятся в их профилях как "был прикреплён".`)) return;
  const r = await fetch("/api/delete_object", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Удалён"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}
async function restoreObject(id, name) {{
  if (!confirm(`Восстановить "${{name}}"?`)) return;
  const r = await fetch("/api/restore_object", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Восстановлен"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}
</script>
</body></html>
"""


def render_objects(search: str, user: str) -> str:
    all_objects = get_objects(include_deleted=True)
    search_low = search.lower().strip()
    if search_low:
        all_objects = [o for o in all_objects if search_low in o["name"].lower()]

    counts = count_workers_per_object()
    rows = []
    for o in all_objects:
        is_deleted = o["deleted_at"] is not None
        status = ('<span class="pill very-late">закрыт</span>' if is_deleted
                  else '<span class="pill early">активен</span>')
        name_link = f'<a href="/object?id={o["id"]}">{html.escape(o["name"])}</a>'
        if is_deleted:
            name_link = f'<span style="text-decoration:line-through; color:var(--muted);">{name_link}</span>'
        cnt = counts.get(o["id"], 0)
        cnt_str = f'<a href="/object?id={o["id"]}" style="color:var(--brand);">{cnt}</a>' if cnt else "—"
        desc = html.escape(o["description"] or "")
        if len(desc) > 80:
            desc = desc[:77] + "…"

        name_for_js = html.escape(json.dumps(o["name"], ensure_ascii=False), quote=True)
        desc_for_js = html.escape(json.dumps(o["description"] or "", ensure_ascii=False), quote=True)
        if is_deleted:
            actions = (
                f'<button class="btn btn-sm" '
                f'onclick="restoreObject({o["id"]}, {name_for_js})">↻ Восстановить</button>'
            )
        else:
            actions = (
                f'<button class="btn btn-sm" '
                f'onclick=\'openEditObject({o["id"]}, {name_for_js}, {desc_for_js})\'>'
                f'✏️ Изменить</button>'
                f'&nbsp;<button class="btn btn-sm btn-danger" '
                f'onclick="delObject({o["id"]}, {name_for_js})">Удалить</button>'
            )
        rows.append(
            f'<tr><td>{name_link}</td>'
            f'<td>{cnt_str}</td>'
            f'<td style="color:var(--muted);font-size:13px;">{desc}</td>'
            f'<td>{status}</td><td>{actions}</td></tr>'
        )

    return _OBJECTS_PAGE.format(
        css=COMMON_CSS,
        topbar=topbar("objects", user),
        search_value=html.escape(search),
        rows="\n".join(rows) if rows else
            '<tr><td colspan="5" style="text-align:center;color:var(--muted);">'
            'Нет объектов. Нажми «➕ Добавить объект»</td></tr>',
        total=len(all_objects),
    )
