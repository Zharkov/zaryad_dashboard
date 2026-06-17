import html
import json

from views.common import COMMON_CSS, topbar
from db.workers import get_workers
from db.credentials import get_all_worker_credentials

_WORKERS_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Работники</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style>
</head><body>
{topbar}
<div class="container">
<h1>👥 Работники</h1>

<div class="actions">
  <button class="btn btn-primary" onclick="openAddWorker()">➕ Добавить работника</button>
</div>

<form method="GET" action="/workers" style="margin-bottom:12px;">
  <input class="search" type="text" name="search" placeholder="🔍 Поиск..."
         value="{search_value}" oninput="this.form.submit()">
</form>

<div style="overflow-x:auto;">
<table>
  <thead><tr><th>Имя</th><th>График</th><th>Статус</th><th>Доступ к сайту</th><th>Действия</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
</div>

<div class="footer">Всего: {total}</div>

</div>

<div class="modal-bg" id="modalAddW" onclick="if(event.target===this)closeAddW()">
  <div class="modal narrow">
    <h3>➕ Добавить работника</h3>
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">ФИО:</label>
      <input type="text" id="addWName" placeholder="Иванов Иван"
             style="width:100%; background:var(--bg); border:1px solid var(--border);
                    border-radius:6px; padding:8px 12px; color:var(--text);
                    font-size:14px; font-family:inherit;">
    </div>
    <div class="row" style="gap:12px;">
      <div style="flex:1;">
        <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Приход:</label>
        <input type="time" id="addWStart" value="09:00" style="width:100%;">
      </div>
      <div style="flex:1;">
        <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Уход:</label>
        <input type="time" id="addWEnd" value="17:00" style="width:100%;">
      </div>
    </div>
    <div style="font-size:12px; color:var(--muted); margin-top:8px;">
      График можно потом изменить кнопкой ✏️ рядом с работником.
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAddW()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAddW()">Создать</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalEditW" onclick="if(event.target===this)closeEditW()">
  <div class="modal narrow">
    <h3 id="editWTitle">Редактирование работника</h3>
    <div style="margin-bottom:10px;">
      <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">ФИО:</label>
      <input type="text" id="editWName"
             style="width:100%; background:var(--bg); border:1px solid var(--border);
                    border-radius:6px; padding:8px 12px; color:var(--text);
                    font-size:14px; font-family:inherit;">
    </div>
    <div class="row" style="gap:12px;">
      <div style="flex:1;">
        <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Приход:</label>
        <input type="time" id="editWStart" style="width:100%;">
      </div>
      <div style="flex:1;">
        <label style="display:block; font-size:12px; color:var(--muted); margin-bottom:4px;">Уход:</label>
        <input type="time" id="editWEnd" style="width:100%;">
      </div>
    </div>
    <div style="font-size:12px; color:var(--muted); margin-top:8px;">
      Переименование сохранит всю историю смен — они привязаны к id, не к имени.<br>
      Изменение графика повлияет только на новые «как обычно» отметки.
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeEditW()">Отмена</button>
      <button class="btn btn-primary" onclick="submitEditW()">Сохранить</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let editingWorkerId = null;

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}}

function openAddWorker() {{
  document.getElementById("addWName").value = "";
  document.getElementById("addWStart").value = "09:00";
  document.getElementById("addWEnd").value = "17:00";
  document.getElementById("modalAddW").classList.add("show");
  setTimeout(() => document.getElementById("addWName").focus(), 100);
}}
function closeAddW() {{ document.getElementById("modalAddW").classList.remove("show"); }}
async function submitAddW() {{
  const name = document.getElementById("addWName").value.trim();
  const ds = document.getElementById("addWStart").value;
  const de = document.getElementById("addWEnd").value;
  if (!name) {{ showToast("Введи ФИО", true); return; }}
  if (!ds || !de) {{ showToast("Укажи график", true); return; }}
  try {{
    const r = await fetch("/api/add_worker", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{name, default_start: ds, default_end: de}}),
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast(`✅ Создан: ${{name}}`);
      closeAddW();
      setTimeout(()=>location.reload(), 500);
    }} else {{
      showToast(d.error || "Ошибка", true);
    }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

function openEditWorker(id, name, ds, de) {{
  editingWorkerId = id;
  document.getElementById("editWTitle").textContent = `✏️ ${{name}}`;
  document.getElementById("editWName").value = name;
  document.getElementById("editWStart").value = ds;
  document.getElementById("editWEnd").value = de;
  document.getElementById("modalEditW").classList.add("show");
}}
function closeEditW() {{ document.getElementById("modalEditW").classList.remove("show"); }}
async function submitEditW() {{
  const name = document.getElementById("editWName").value.trim();
  const ds = document.getElementById("editWStart").value;
  const de = document.getElementById("editWEnd").value;
  if (!name) {{ showToast("Введи ФИО", true); return; }}
  try {{
    const r = await fetch("/api/update_worker", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{id: editingWorkerId, name, default_start: ds, default_end: de}}),
    }});
    const d = await r.json();
    if (d.ok) {{
      showToast("✅ Сохранено");
      closeEditW();
      setTimeout(()=>location.reload(), 500);
    }} else {{
      showToast(d.error || "Ошибка", true);
    }}
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

async function softDel(id, name) {{
  if (!confirm(`Удалить ${{name}}? (история смен сохранится)`)) return;
  const r = await fetch("/api/soft_delete_worker", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Удалён"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}
async function hardDel(id, name) {{
  if (!confirm(`⚠ УДАЛИТЬ ${{name}} НАВСЕГДА со всей историей смен? Это нельзя отменить!`)) return;
  if (!confirm(`Точно удалить ${{name}} и ВСЕ его смены?`)) return;
  const r = await fetch("/api/hard_delete_worker", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Удалён навсегда"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}
async function restore(id, name) {{
  if (!confirm(`Восстановить ${{name}}?`)) return;
  const r = await fetch("/api/restore_worker", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Восстановлен"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}

function copyPw(workerId) {{
  const el = document.getElementById("pw_" + workerId);
  if (!el) return;
  const text = el.textContent;
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(text).then(
      () => showToast("Пароль скопирован"),
      () => showToast("Не удалось скопировать", true)
    );
  }} else {{
    showToast("Выдели и скопируй вручную", true);
  }}
}}
async function createAccess(id, name) {{
  if (!confirm(`Создать доступ для ${{name}}? Будет сгенерирован пароль.`)) return;
  const r = await fetch("/api/create_worker_access", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{
    alert(`Доступ создан для ${{name}}\\n\\nЛогин: ${{id}}\\nПароль: ${{d.password}}\\n\\nЗапиши и передай работнику.\\nПароль также виден в таблице.`);
    setTimeout(()=>location.reload(), 200);
  }} else showToast(d.error || "Ошибка", true);
}}
async function resetAccess(id, name) {{
  if (!confirm(`Сбросить пароль для ${{name}}? Старый перестанет работать.`)) return;
  const r = await fetch("/api/reset_worker_access", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{
    alert(`Новый пароль для ${{name}}:\\n\\nЛогин: ${{id}}\\nПароль: ${{d.password}}`);
    setTimeout(()=>location.reload(), 200);
  }} else showToast(d.error || "Ошибка", true);
}}
async function blockAccess(id, name) {{
  if (!confirm(`Заблокировать доступ ${{name}}? Не сможет войти на сайт.`)) return;
  const r = await fetch("/api/block_worker_access", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Заблокирован"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}
async function unblockAccess(id, name) {{
  const r = await fetch("/api/unblock_worker_access", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}})
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Разблокирован"); setTimeout(()=>location.reload(), 400); }}
  else showToast(d.error || "Ошибка", true);
}}
</script>
</body></html>
"""


def render_workers(search: str, user: str) -> str:
    all_workers = get_workers(include_deleted=True)
    search_low = search.lower().strip()
    if search_low:
        all_workers = [w for w in all_workers if search_low in w["name"].lower()]

    creds = get_all_worker_credentials()
    rows = []

    for w in all_workers:
        is_deleted = w["deleted_at"] is not None
        status = '<span class="pill very-late">удалён</span>' if is_deleted \
                 else '<span class="pill early">активен</span>'
        name_link = f'<a href="/worker?id={w["id"]}">{html.escape(w["name"])}</a>'
        if is_deleted:
            name_link = f'<span style="text-decoration:line-through; color:var(--muted);">{name_link}</span>'

        name_for_js = html.escape(json.dumps(w["name"], ensure_ascii=False), quote=True)

        if is_deleted:
            access_cell = '<span style="color:var(--muted); font-size:12px;">—</span>'
        else:
            c = creds.get(w["id"])
            if not c:
                access_cell = (
                    f'<button class="btn btn-sm btn-primary" '
                    f'onclick="createAccess({w["id"]}, {name_for_js})">'
                    f'🔑 Создать доступ</button>'
                )
            else:
                pw = html.escape(c["password"])
                blocked_pill = ('<span class="pill very-late" style="margin-left:6px;">'
                                '🚫 блок</span>' if c["blocked"] else '')
                access_cell = (
                    f'<div style="display:flex; flex-direction:column; gap:4px;">'
                    f'<div style="font-size:12px;">'
                    f'<span style="color:var(--muted);">логин:</span> '
                    f'<code style="background:var(--bg); padding:1px 6px; border-radius:3px;">{w["id"]}</code>'
                    f'</div>'
                    f'<div style="font-size:12px;">'
                    f'<span style="color:var(--muted);">пароль:</span> '
                    f'<code id="pw_{w["id"]}" style="background:var(--bg); padding:1px 6px; border-radius:3px; user-select:all; cursor:pointer;" '
                    f'onclick="copyPw({w["id"]})" title="Клик чтобы скопировать">{pw}</code>'
                    f'{blocked_pill}'
                    f'</div>'
                    f'<div style="display:flex; gap:4px; margin-top:4px;">'
                    f'<button class="btn btn-sm" style="padding:2px 8px; font-size:11px;" '
                    f'onclick="resetAccess({w["id"]}, {name_for_js})">🔄 Сбросить</button>'
                )
                if c["blocked"]:
                    access_cell += (
                        f'<button class="btn btn-sm" style="padding:2px 8px; font-size:11px;" '
                        f'onclick="unblockAccess({w["id"]}, {name_for_js})">✅ Разблокировать</button>'
                    )
                else:
                    access_cell += (
                        f'<button class="btn btn-sm btn-danger" style="padding:2px 8px; font-size:11px;" '
                        f'onclick="blockAccess({w["id"]}, {name_for_js})">🚫 Заблокировать</button>'
                    )
                access_cell += '</div></div>'

        if is_deleted:
            actions = (
                f'<button class="btn btn-sm" onclick="restore({w["id"]}, {name_for_js})">'
                f'↻ Восстановить</button>'
                f'&nbsp;<button class="btn btn-sm btn-danger" '
                f'onclick="hardDel({w["id"]}, {name_for_js})">'
                f'🗑 Удалить навсегда</button>'
            )
        else:
            actions = (
                f'<button class="btn btn-sm" '
                f'onclick=\'openEditWorker({w["id"]}, {name_for_js}, '
                f'"{w["default_start"]}", "{w["default_end"]}")\'>'
                f'✏️ Изменить</button>'
                f'&nbsp;<button class="btn btn-sm btn-danger" '
                f'onclick="softDel({w["id"]}, {name_for_js})">Удалить</button>'
            )
        rows.append(
            f'<tr><td>{name_link}</td>'
            f'<td>{w["default_start"]}-{w["default_end"]}</td>'
            f'<td>{status}</td>'
            f'<td>{access_cell}</td>'
            f'<td>{actions}</td></tr>'
        )

    return _WORKERS_PAGE.format(
        css=COMMON_CSS,
        topbar=topbar("workers", user),
        search_value=html.escape(search),
        rows="\n".join(rows) if rows else
            '<tr><td colspan="5" style="text-align:center;color:var(--muted);">Нет</td></tr>',
        total=len(all_workers),
    )
