import html
import json

from views.common import topbar
from db.admin_users import list_admins
from db.credentials import get_workers_with_access

_USERS_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Пользователи</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css?v=7">
</head><body>
{topbar}
<div class="container">
<h1>👥 Пользователи</h1>

<div class="actions">
  <button class="btn btn-primary" onclick="openAdd()">+ Добавить</button>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="filterRole('all', this)">Все ({count_all})</button>
  <button class="tab-btn" onclick="filterRole('admin', this)">👑 Администраторы ({count_admin})</button>
  <button class="tab-btn" onclick="filterRole('accountant', this)">📊 Бухгалтеры ({count_accountant})</button>
  <button class="tab-btn" onclick="filterRole('worker', this)">👷 Работники ({count_worker})</button>
</div>

<div class="scroll-x">
<table>
  <thead><tr>
    <th>Логин / Имя</th><th>Роль</th><th>Добавлен</th><th>Статус</th><th>Действия</th>
  </tr></thead>
  <tbody id="usersBody">
{rows}
  </tbody>
</table>
</div>
</div>

<div class="modal-bg" id="modalAdd" onclick="if(event.target===this)closeAdd()">
  <div class="modal narrow">
    <h3>Добавить пользователя</h3>
    <div class="row">
      <label class="label-w">Логин:</label>
      <input type="text" id="addLogin" class="input-full" autocomplete="off">
    </div>
    <div class="row">
      <label class="label-w">Пароль:</label>
      <input type="password" id="addPassword" class="input-full" autocomplete="new-password">
    </div>
    <div class="row">
      <label class="label-w">Роль:</label>
      <select id="addRole" class="input-full">
        <option value="admin">👑 Администратор</option>
        <option value="accountant">📊 Бухгалтер</option>
      </select>
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAdd()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAdd()">Добавить</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalPasswd" onclick="if(event.target===this)closePasswd()">
  <div class="modal narrow">
    <h3 id="passwdTitle">Смена пароля</h3>
    <div class="row">
      <label class="label-w">Новый пароль:</label>
      <input type="password" id="newPassword" class="input-full" autocomplete="new-password">
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closePasswd()">Отмена</button>
      <button class="btn btn-primary" onclick="submitPasswd()">Сохранить</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>
<script>
const ME = {me_js};

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}}

function filterRole(role, btn) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#usersBody tr').forEach(tr => {{
    tr.style.display = (role === 'all' || tr.dataset.role === role) ? '' : 'none';
  }});
}}

function openAdd() {{
  document.getElementById('addLogin').value = '';
  document.getElementById('addPassword').value = '';
  document.getElementById('addRole').value = 'admin';
  document.getElementById('modalAdd').classList.add('show');
}}
function closeAdd() {{ document.getElementById('modalAdd').classList.remove('show'); }}

async function submitAdd() {{
  const username = document.getElementById('addLogin').value.trim();
  const password = document.getElementById('addPassword').value.trim();
  const role = document.getElementById('addRole').value;
  if (!username || !password) {{ showToast('Заполни все поля', true); return; }}
  try {{
    const r = await fetch('/api/add_user', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{username, password, role}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Добавлен'); closeAdd(); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}

let _passwdTarget = null, _passwdType = 'user';
function openPasswd(username) {{
  _passwdTarget = username; _passwdType = 'user';
  document.getElementById('passwdTitle').textContent = 'Смена пароля · ' + username;
  document.getElementById('newPassword').value = '';
  document.getElementById('modalPasswd').classList.add('show');
}}
function openWorkerPasswd(workerId, workerName) {{
  _passwdTarget = workerId; _passwdType = 'worker';
  document.getElementById('passwdTitle').textContent = 'Смена пароля · ' + workerName;
  document.getElementById('newPassword').value = '';
  document.getElementById('modalPasswd').classList.add('show');
}}
function closePasswd() {{ document.getElementById('modalPasswd').classList.remove('show'); }}

async function submitPasswd() {{
  const password = document.getElementById('newPassword').value.trim();
  if (!password) {{ showToast('Введи новый пароль', true); return; }}
  const url = _passwdType === 'worker' ? '/api/set_worker_password' : '/api/change_user_password';
  const body = _passwdType === 'worker'
    ? {{worker_id: _passwdTarget, password}}
    : {{username: _passwdTarget, password}};
  try {{
    const r = await fetch(url, {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(body),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Пароль изменён'); closePasswd(); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}

async function changeRole(username, newRole) {{
  const label = newRole === 'admin' ? 'Администратор' : 'Бухгалтер';
  if (!confirm('Изменить роль «' + username + '» на «' + label + '»?')) return;
  try {{
    const r = await fetch('/api/change_user_role', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{username, role: newRole}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Роль изменена'); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}

async function deleteWorkerAccess(workerId, workerName) {{
  if (!confirm('Удалить доступ «' + workerName + '»? Работник останется в системе, но не сможет войти.')) return;
  try {{
    const r = await fetch('/api/delete_worker_access', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{worker_id: workerId}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Доступ удалён'); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}

async function deleteUser(username) {{
  if (!confirm('Удалить пользователя «' + username + '»?')) return;
  try {{
    const r = await fetch('/api/delete_user', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{username}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast('Удалён'); setTimeout(() => location.reload(), 400); }}
    else showToast(d.error || 'Ошибка', true);
  }} catch(e) {{ showToast('Сеть: ' + e.message, true); }}
}}
</script>
</body></html>
"""


def render_users(user: str) -> str:
    admins = list_admins()
    workers = get_workers_with_access()

    counts = {"admin": 0, "accountant": 0, "worker": len(workers)}
    rows = []

    for a in admins:
        role = a["role"] or "admin"
        counts[role] += 1
        created = a["created_at"][:10] if a["created_at"] else "—"
        is_me = a["username"] == user
        uname_esc = html.escape(a["username"])
        # Single-quoted JS string inside double-quoted HTML attribute
        uname_js = "'" + a["username"].replace("\\", "\\\\").replace("'", "\\'") + "'"

        if role == "admin":
            role_pill = '<span class="pill brand">👑 Администратор</span>'
            role_btn = (
                f'<button class="btn btn-sm" onclick="changeRole({uname_js}, \'accountant\')">'
                f'→ Бухгалтер</button> '
            ) if not is_me else ''
        else:
            role_pill = '<span class="pill info">📊 Бухгалтер</span>'
            role_btn = (
                f'<button class="btn btn-sm" onclick="changeRole({uname_js}, \'admin\')">'
                f'→ Администратор</button> '
            )

        me_badge = ' <span class="text-sm-muted">(вы)</span>' if is_me else ''
        del_btn = (
            f'<button class="btn btn-sm btn-danger" onclick="deleteUser({uname_js})">× Удалить</button>'
        ) if not is_me else ''

        rows.append(
            f'<tr data-role="{role}">'
            f'<td><strong>{uname_esc}</strong>{me_badge}</td>'
            f'<td>{role_pill}</td>'
            f'<td class="text-sm-muted">{created}</td>'
            f'<td>—</td>'
            f'<td>'
            f'{role_btn}'
            f'<button class="btn btn-sm" onclick="openPasswd({uname_js})">🔑 Пароль</button> '
            f'{del_btn}'
            f'</td>'
            f'</tr>'
        )

    for w in workers:
        created = w["created_at"][:10] if w["created_at"] else "—"
        is_blocked = bool(w["blocked"])
        status = (
            '<span class="pill bad">🔒 Заблокирован</span>'
            if is_blocked else
            '<span class="pill ok">✓ Активен</span>'
        )
        wname_js = "'" + w["name"].replace("\\", "\\\\").replace("'", "\\'") + "'"
        rows.append(
            f'<tr data-role="worker">'
            f'<td><a href="/worker?id={w["id"]}">{html.escape(w["name"])}</a>'
            f' <span class="text-sm-muted">ID: {w["id"]}</span></td>'
            f'<td><span class="pill">👷 Работник</span></td>'
            f'<td class="text-sm-muted">{created}</td>'
            f'<td>{status}</td>'
            f'<td>'
            f'<a class="btn btn-sm" href="/worker?id={w["id"]}">→ Профиль</a> '
            f'<button class="btn btn-sm" onclick="openWorkerPasswd({w["id"]}, {wname_js})">🔑 Пароль</button> '
            f'<button class="btn btn-sm btn-danger" onclick="deleteWorkerAccess({w["id"]}, {wname_js})">× Удалить</button>'
            f'</td>'
            f'</tr>'
        )

    count_all = counts["admin"] + counts["accountant"] + counts["worker"]

    return _USERS_PAGE.format(
        topbar=topbar("users", user),
        me_js=json.dumps(user),
        rows="\n".join(rows) if rows else
            '<tr><td colspan="5" class="empty-cell">Нет пользователей</td></tr>',
        count_all=count_all,
        count_admin=counts["admin"],
        count_accountant=counts["accountant"],
        count_worker=counts["worker"],
    )
