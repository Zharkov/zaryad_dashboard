import html
import json

from views.common import topbar
from db.workers import get_workers
from db.skills import get_all_skills, get_worker_skills_map
from db.compat import get_compat_matrix
from db.crews import get_crews, count_workers_per_crew

_CREWS_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Бригады</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css?v=13">
</head><body>
{topbar}
<div class="container">
<h1>🧩 Бригады</h1>
<p class="text-sm-muted">
  База знаний о сотрудниках: качества и направленная совместимость.
  На её основе собираются бригады.
</p>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('skills', this)">⭐ Качества</button>
  <button class="tab-btn" onclick="switchTab('compat', this); if(!graphBuilt) buildGraph();">🤝 Совместимость</button>
  <button class="tab-btn" onclick="switchTab('teams', this)">🧩 Бригады ({crew_count})</button>
</div>

<div id="tab_skills" class="tab-panel active">
  <div class="card skill-catalog-card">
    <div class="skill-catalog-head">
      <strong>🛠 Навыки</strong>
      <span class="text-sm-muted">То, что человек умеет делать: сварка, работа с лопатой, вождение...</span>
    </div>
    <div class="skill-catalog-list">{skill_catalog_chips_skill}</div>
    <div class="skill-add-row">
      <input type="text" id="newSkillName" class="input-full"
             placeholder="Например: Сварка, Вождение погрузчика..." onkeydown="if(event.key==='Enter')addSkill('skill')">
      <button class="btn btn-primary" onclick="addSkill('skill')">➕ Добавить навык</button>
    </div>
  </div>

  <div class="card skill-catalog-card mt-md">
    <div class="skill-catalog-head">
      <strong>🎭 Черты характера</strong>
      <span class="text-sm-muted">Плюсы и минусы поведения: пунктуальность, аккуратность, конфликтность...</span>
    </div>
    <div class="skill-catalog-list">{skill_catalog_chips_trait}</div>
    <div class="skill-add-row">
      <input type="text" id="newTraitName" class="input-full"
             placeholder="Например: Пунктуальность, Конфликтность..." onkeydown="if(event.key==='Enter')addSkill('trait')">
      <button class="btn btn-primary" onclick="addSkill('trait')">➕ Добавить черту</button>
    </div>
  </div>

  <div class="scroll-x mt-md">
  <table>
    <thead><tr><th>Сотрудник</th><th>🛠 Навыки</th><th>🎭 Черты</th><th></th></tr></thead>
    <tbody>{worker_skill_rows}</tbody>
  </table>
  </div>
</div>

<div id="tab_compat" class="tab-panel">
  <p class="text-sm-muted">
    Оценка направленная: «А → Б» может отличаться от «Б → А».
  </p>
  <div class="compat-view-toggle">
    <button class="filter-chip active" id="compatViewGraphBtn" onclick="showCompatView('graph')">🕸 Граф</button>
    <button class="filter-chip" id="compatViewTableBtn" onclick="showCompatView('table')">📋 Таблица</button>
  </div>

  <div id="compatGraphView">
    <div class="graph-add-row">
      <select id="graphFromSelect" class="filter-select"></select>
      <span class="text-sm-muted">→</span>
      <select id="graphToSelect" class="filter-select"></select>
      <button class="btn btn-sm btn-primary" onclick="openCompatFromSelects()">Оценить связь</button>
    </div>
    <div class="compat-graph-wrap" id="compatGraphWrap">
      <svg id="compatSvg" xmlns="http://www.w3.org/2000/svg"></svg>
    </div>
    <div class="hint">
      Кружки можно перетаскивать. Клик по кружку — подсветить его связи. Клик по линии — изменить оценку.
      Зелёное — притягивает, красное — отталкивает, чем толще линия — тем сильнее.
    </div>
  </div>

  <div id="compatTableView" style="display:none">
    <div class="scroll-x compat-scroll">
    <table class="compat-table">
      <thead><tr><th></th>{compat_head}</tr></thead>
      <tbody>{compat_rows}</tbody>
    </table>
    </div>
  </div>
</div>

<div id="tab_teams" class="tab-panel">
  <div class="actions">
    <button class="btn btn-primary" onclick="openAddCrew()">➕ Создать бригаду</button>
  </div>
  <div class="scroll-x">
  <table>
    <thead><tr><th>Название</th><th>Заметка</th><th>Состав</th><th>Действия</th></tr></thead>
    <tbody>{crew_rows}</tbody>
  </table>
  </div>
</div>

<div class="footer">Сотрудников: {worker_count}</div>
</div>

<div class="modal-bg" id="modalSkill" onclick="if(event.target===this)closeSkillModal()">
  <div class="modal narrow">
    <h3 id="skillModalTitle">Оценить качество</h3>
    <div class="mb-field">
      <label class="field-label">Качество:</label>
      <select id="skillSelect" class="input-full" onchange="onSkillSelectChange()"></select>
    </div>
    <div class="mb-field">
      <label class="field-label">Оценка:</label>
      <div class="rating-picker" id="ratingPicker">
        <button type="button" onclick="pickRating(1)" data-r="1">1</button>
        <button type="button" onclick="pickRating(2)" data-r="2">2</button>
        <button type="button" onclick="pickRating(3)" data-r="3">3</button>
        <button type="button" onclick="pickRating(4)" data-r="4">4</button>
        <button type="button" onclick="pickRating(5)" data-r="5">5</button>
      </div>
      <div class="hint">1 — слабо, 5 — отлично</div>
    </div>
    <div class="mb-field">
      <label class="field-label">Заметка (необязательно):</label>
      <input type="text" id="skillNote" class="input-full" placeholder="Например: отлично варит горизонтальные швы">
    </div>
    <div class="footer-btns">
      <button class="btn btn-danger" id="skillDeleteBtn" onclick="deleteSkillRating()" style="display:none">Удалить оценку</button>
      <button class="btn" onclick="closeSkillModal()">Отмена</button>
      <button class="btn btn-primary" onclick="submitSkillRating()">Сохранить</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalCompat" onclick="if(event.target===this)closeCompatModal()">
  <div class="modal narrow">
    <h3 id="compatModalTitle">Совместимость</h3>
    <div class="mb-field">
      <label class="field-label">Оценка:</label>
      <div class="rating-picker compat-picker" id="compatPicker">
        <button type="button" onclick="pickCompat(-2)" data-r="-2">-2</button>
        <button type="button" onclick="pickCompat(-1)" data-r="-1">-1</button>
        <button type="button" onclick="pickCompat(0)" data-r="0">0</button>
        <button type="button" onclick="pickCompat(1)" data-r="1">+1</button>
        <button type="button" onclick="pickCompat(2)" data-r="2">+2</button>
      </div>
      <div class="hint">-2 конфликт · -1 не очень · 0 нейтрально · +1 хорошо · +2 отлично сработались</div>
    </div>
    <div class="mb-field">
      <label class="field-label">Заметка (необязательно):</label>
      <input type="text" id="compatNote" class="input-full">
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeCompatModal()">Отмена</button>
      <button class="btn btn-primary" onclick="submitCompat()">Сохранить</button>
    </div>
  </div>
</div>

<div class="modal-bg" id="modalAddCrew" onclick="if(event.target===this)closeAddCrew()">
  <div class="modal narrow">
    <h3>➕ Создать бригаду</h3>
    <div class="mb-field">
      <label class="field-label">Название:</label>
      <input type="text" id="addCrewName" class="input-full" placeholder="Например: Бригада №1">
    </div>
    <div class="mb-field">
      <label class="field-label">Заметка (необязательно):</label>
      <input type="text" id="addCrewNote" class="input-full">
    </div>
    <div class="footer-btns">
      <button class="btn" onclick="closeAddCrew()">Отмена</button>
      <button class="btn btn-primary" onclick="submitAddCrew()">Создать</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const SKILLS = {skills_json};
const WORKER_SKILLS = {worker_skills_json};
const COMPAT = {compat_json};
const COMPAT_WORKERS = {compat_workers_json};

// ---- skills ----
let curSkillWorkerId = null;
let curSkillRating = null;

async function addSkill(kind) {{
  const elId = kind === 'trait' ? 'newTraitName' : 'newSkillName';
  const el = document.getElementById(elId);
  const name = el.value.trim();
  if (!name) {{ showToast("Введи название", true); return; }}
  try {{
    const r = await fetch("/api/add_skill", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{name, kind}}),
    }});
    const d = await r.json();
    if (d.ok) {{ el.value = ""; setTimeout(()=>location.reload(), 300); }}
    else showToast(d.error || "Ошибка", true);
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

async function deleteSkillFromCatalog(id, name) {{
  if (!confirm(`Удалить «${{name}}» из каталога? Оценки по нему у сотрудников тоже пропадут.`)) return;
  const r = await fetch("/api/delete_skill", {{
    method: "POST", headers: {{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}}),
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Удалено"); setTimeout(()=>location.reload(), 300); }}
  else showToast(d.error || "Ошибка", true);
}}

function openSkillModal(workerId, preselectSkillId) {{
  curSkillWorkerId = workerId;
  const sel = document.getElementById("skillSelect");
  const skillsGroup = SKILLS.filter(s => s.kind !== 'trait');
  const traitsGroup = SKILLS.filter(s => s.kind === 'trait');
  let optHtml = "";
  if (skillsGroup.length) optHtml += `<optgroup label="🛠 Навыки">${{skillsGroup.map(s => `<option value="${{s.id}}">${{s.name}}</option>`).join("")}}</optgroup>`;
  if (traitsGroup.length) optHtml += `<optgroup label="🎭 Черты">${{traitsGroup.map(s => `<option value="${{s.id}}">${{s.name}}</option>`).join("")}}</optgroup>`;
  sel.innerHTML = optHtml;
  if (preselectSkillId) sel.value = preselectSkillId;
  onSkillSelectChange();
  document.getElementById("modalSkill").classList.add("show");
}}
function closeSkillModal() {{ document.getElementById("modalSkill").classList.remove("show"); }}

function onSkillSelectChange() {{
  const skillId = parseInt(document.getElementById("skillSelect").value);
  const existing = (WORKER_SKILLS[curSkillWorkerId] || []).find(x => x.skill_id === skillId);
  document.getElementById("skillNote").value = existing ? (existing.note || "") : "";
  pickRating(existing ? existing.rating : 3);
  document.getElementById("skillDeleteBtn").style.display = existing ? "inline-block" : "none";
}}

function pickRating(r) {{
  curSkillRating = r;
  document.querySelectorAll("#ratingPicker button").forEach(b => {{
    b.classList.toggle("active", parseInt(b.dataset.r) === r);
  }});
}}

async function submitSkillRating() {{
  const skillId = parseInt(document.getElementById("skillSelect").value);
  const note = document.getElementById("skillNote").value.trim();
  try {{
    const r = await fetch("/api/set_worker_skill", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{worker_id: curSkillWorkerId, skill_id: skillId, rating: curSkillRating, note}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Сохранено"); closeSkillModal(); setTimeout(()=>location.reload(), 300); }}
    else showToast(d.error || "Ошибка", true);
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

async function deleteSkillRating() {{
  const skillId = parseInt(document.getElementById("skillSelect").value);
  const r = await fetch("/api/delete_worker_skill", {{
    method: "POST", headers: {{"Content-Type":"application/json"}},
    body: JSON.stringify({{worker_id: curSkillWorkerId, skill_id: skillId}}),
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Оценка удалена"); closeSkillModal(); setTimeout(()=>location.reload(), 300); }}
  else showToast(d.error || "Ошибка", true);
}}

// ---- compat ----
let curCompatFrom = null;
let curCompatTo = null;
let curCompatScore = 0;

function showCompatView(v) {{
  document.getElementById('compatGraphView').style.display = v === 'graph' ? '' : 'none';
  document.getElementById('compatTableView').style.display = v === 'table' ? '' : 'none';
  document.getElementById('compatViewGraphBtn').classList.toggle('active', v === 'graph');
  document.getElementById('compatViewTableBtn').classList.toggle('active', v === 'table');
}}

function openCompatModal(fromId, fromName, toId, toName) {{
  curCompatFrom = fromId; curCompatTo = toId;
  document.getElementById("compatModalTitle").textContent = `${{fromName}} → ${{toName}}`;
  const key = fromId + "_" + toId;
  const existing = COMPAT[key];
  document.getElementById("compatNote").value = existing ? (existing[1] || "") : "";
  pickCompat(existing ? existing[0] : 0);
  document.getElementById("modalCompat").classList.add("show");
}}
function closeCompatModal() {{ document.getElementById("modalCompat").classList.remove("show"); }}

function openCompatFromSelects() {{
  const f = parseInt(document.getElementById('graphFromSelect').value);
  const t = parseInt(document.getElementById('graphToSelect').value);
  if (f === t) {{ showToast('Выбери разных сотрудников', true); return; }}
  const wf = COMPAT_WORKERS.find(w => w.id === f);
  const wt = COMPAT_WORKERS.find(w => w.id === t);
  openCompatModal(f, wf.name, t, wt.name);
}}

function pickCompat(r) {{
  curCompatScore = r;
  document.querySelectorAll("#compatPicker button").forEach(b => {{
    b.classList.toggle("active", parseInt(b.dataset.r) === r);
  }});
}}

async function submitCompat() {{
  const note = document.getElementById("compatNote").value.trim();
  try {{
    const r = await fetch("/api/set_compat", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{from_worker_id: curCompatFrom, to_worker_id: curCompatTo, score: curCompatScore, note}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("Сохранено"); closeCompatModal(); setTimeout(()=>location.reload(), 300); }}
    else showToast(d.error || "Ошибка", true);
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}

// ---- compat graph (force-directed, hand-rolled, no external libs) ----
let graphBuilt = false;
const NS = "http://www.w3.org/2000/svg";

document.getElementById("graphFromSelect").innerHTML =
  COMPAT_WORKERS.map(w => `<option value="${{w.id}}">${{w.name}}</option>`).join("");
document.getElementById("graphToSelect").innerHTML =
  COMPAT_WORKERS.map(w => `<option value="${{w.id}}">${{w.name}}</option>`).join("");
if (COMPAT_WORKERS.length > 1) document.getElementById("graphToSelect").selectedIndex = 1;

function initials(name) {{
  const parts = name.trim().split(/\\s+/);
  return parts.slice(0, 2).map(p => p[0] || "").join("").toUpperCase();
}}

function ccClass(score) {{
  if (score <= -2) return "cc-2";
  if (score === -1) return "cc-1";
  if (score === 0) return "cc0";
  if (score === 1) return "cc1";
  return "cc2";
}}

function buildGraph() {{
  graphBuilt = true;
  const wrap = document.getElementById("compatGraphWrap");
  const svg = document.getElementById("compatSvg");
  const W = wrap.clientWidth || 800;
  const H = 520;
  svg.setAttribute("viewBox", `0 0 ${{W}} ${{H}}`);

  const nodes = COMPAT_WORKERS.map((w, i) => {{
    const angle = (2 * Math.PI * i) / Math.max(1, COMPAT_WORKERS.length);
    const R = Math.min(W, H) / 3;
    return {{id: w.id, name: w.name, x: W/2 + Math.cos(angle)*R, y: H/2 + Math.sin(angle)*R, vx: 0, vy: 0}};
  }});
  const byId = {{}};
  nodes.forEach(n => byId[n.id] = n);

  const edges = [];
  Object.keys(COMPAT).forEach(key => {{
    const parts = key.split("_");
    const f = parseInt(parts[0]), t = parseInt(parts[1]);
    const entry = COMPAT[key];
    if (byId[f] && byId[t]) edges.push({{from: f, to: t, score: entry[0], note: entry[1]}});
  }});

  const REPEL = 14000, SPRING = 0.02, CENTER = 0.015, DAMPING = 0.82;
  for (let iter = 0; iter < 400; iter++) {{
    nodes.forEach(n => {{ n.fx = 0; n.fy = 0; }});
    for (let i = 0; i < nodes.length; i++) {{
      for (let j = i + 1; j < nodes.length; j++) {{
        const a = nodes[i], b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist2 = Math.max(dx*dx + dy*dy, 25);
        const dist = Math.sqrt(dist2);
        const f = REPEL / dist2;
        const fx = (dx/dist)*f, fy = (dy/dist)*f;
        a.fx += fx; a.fy += fy;
        b.fx -= fx; b.fy -= fy;
      }}
    }}
    edges.forEach(e => {{
      const a = byId[e.from], b = byId[e.to];
      const rest = 160 - e.score * 35;
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.sqrt(dx*dx + dy*dy) || 0.01;
      const f = SPRING * (dist - rest);
      const fx = (dx/dist)*f, fy = (dy/dist)*f;
      a.fx += fx; a.fy += fy;
      b.fx -= fx; b.fy -= fy;
    }});
    nodes.forEach(n => {{
      n.fx += (W/2 - n.x) * CENTER;
      n.fy += (H/2 - n.y) * CENTER;
      n.vx = (n.vx + n.fx) * DAMPING;
      n.vy = (n.vy + n.fy) * DAMPING;
      n.x += n.vx * 0.05;
      n.y += n.vy * 0.05;
      n.x = Math.max(34, Math.min(W - 34, n.x));
      n.y = Math.max(34, Math.min(H - 34, n.y));
    }});
  }}

  svg.innerHTML = "";
  const defs = document.createElementNS(NS, "defs");
  ["cc-2", "cc-1", "cc0", "cc1", "cc2"].forEach(cls => {{
    const marker = document.createElementNS(NS, "marker");
    marker.setAttribute("id", "arrow-" + cls);
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "9"); marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "7"); marker.setAttribute("markerHeight", "7");
    marker.setAttribute("orient", "auto-start-reverse");
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", "M0,0 L10,5 L0,10 z");
    path.setAttribute("class", "graph-arrow " + cls);
    marker.appendChild(path);
    defs.appendChild(marker);
  }});
  svg.appendChild(defs);

  const edgesGroup = document.createElementNS(NS, "g");
  svg.appendChild(edgesGroup);
  const nodesGroup = document.createElementNS(NS, "g");
  svg.appendChild(nodesGroup);

  const edgeEls = [];
  edges.forEach(e => {{
    const a = byId[e.from], b = byId[e.to];
    const cls = ccClass(e.score);
    const sign = e.from < e.to ? 1 : -1;
    const path = document.createElementNS(NS, "path");
    path.setAttribute("class", "graph-edge " + cls);
    path.setAttribute("marker-end", `url(#arrow-${{cls}})`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke-width", 1.5 + Math.abs(e.score) * 1.2);
    path.style.cursor = "pointer";
    path.addEventListener("click", () => openCompatModal(e.from, a.name, e.to, b.name));
    const titleEl = document.createElementNS(NS, "title");
    titleEl.textContent = `${{a.name}} → ${{b.name}}: ${{e.score > 0 ? "+" + e.score : e.score}}${{e.note ? " · " + e.note : ""}}`;
    path.appendChild(titleEl);
    edgesGroup.appendChild(path);
    edgeEls.push({{path, a, b, sign}});
  }});

  const nodeEls = [];
  nodes.forEach(n => {{
    const g = document.createElementNS(NS, "g");
    g.setAttribute("class", "graph-node");
    const circle = document.createElementNS(NS, "circle");
    circle.setAttribute("r", 20);
    g.appendChild(circle);
    const text = document.createElementNS(NS, "text");
    text.setAttribute("class", "graph-node-initials");
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("dy", 4);
    text.textContent = initials(n.name);
    g.appendChild(text);
    const label = document.createElementNS(NS, "text");
    label.setAttribute("class", "graph-node-label");
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("dy", 34);
    label.textContent = n.name;
    g.appendChild(label);
    nodesGroup.appendChild(g);
    nodeEls.push({{g, n}});

    let dragging = false;
    g.addEventListener("mousedown", (ev) => {{ dragging = true; ev.preventDefault(); }});
    window.addEventListener("mousemove", (ev) => {{
      if (!dragging) return;
      const rect = svg.getBoundingClientRect();
      n.x = (ev.clientX - rect.left) * (W / rect.width);
      n.y = (ev.clientY - rect.top) * (H / rect.height);
      render();
    }});
    window.addEventListener("mouseup", () => {{ dragging = false; }});
    g.addEventListener("click", (ev) => {{ if (!dragging) highlightNode(n.id); }});
  }});

  function render() {{
    nodeEls.forEach(({{g, n}}) => {{ g.setAttribute("transform", `translate(${{n.x}},${{n.y}})`); }});
    edgeEls.forEach(({{path, a, b, sign}}) => {{
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.sqrt(dx*dx + dy*dy) || 1;
      const nx = -dy / dist, ny = dx / dist;
      const curve = 18 * sign;
      const mx = (a.x + b.x)/2 + nx*curve, my = (a.y + b.y)/2 + ny*curve;
      path.setAttribute("d", `M${{a.x}},${{a.y}} Q${{mx}},${{my}} ${{b.x}},${{b.y}}`);
    }});
  }}
  render();

  let highlighted = null;
  window.highlightNode = function(id) {{
    highlighted = (highlighted === id) ? null : id;
    nodeEls.forEach(({{g, n}}) => {{
      const related = highlighted === null || n.id === highlighted ||
        edges.some(e => (e.from === highlighted && e.to === n.id) || (e.to === highlighted && e.from === n.id));
      g.classList.toggle("dim", !related);
      g.classList.toggle("graph-node-active", n.id === highlighted);
    }});
    edgeEls.forEach(({{path}}, idx) => {{
      const e = edges[idx];
      const related = highlighted === null || e.from === highlighted || e.to === highlighted;
      path.classList.toggle("dim", !related);
    }});
  }};
}}

// ---- crews ----
function openAddCrew() {{
  document.getElementById("addCrewName").value = "";
  document.getElementById("addCrewNote").value = "";
  document.getElementById("modalAddCrew").classList.add("show");
  setTimeout(() => document.getElementById("addCrewName").focus(), 100);
}}
function closeAddCrew() {{ document.getElementById("modalAddCrew").classList.remove("show"); }}
async function submitAddCrew() {{
  const name = document.getElementById("addCrewName").value.trim();
  const note = document.getElementById("addCrewNote").value.trim();
  if (!name) {{ showToast("Введи название", true); return; }}
  try {{
    const r = await fetch("/api/add_crew", {{
      method: "POST", headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify({{name, note}}),
    }});
    const d = await r.json();
    if (d.ok) {{ showToast("✅ Создана"); closeAddCrew(); setTimeout(()=>location.href="/crew?id="+d.id, 400); }}
    else showToast(d.error || "Ошибка", true);
  }} catch (e) {{ showToast("Сеть: " + e.message, true); }}
}}
async function deleteCrewFromList(id, name) {{
  if (!confirm(`Удалить бригаду «${{name}}»?`)) return;
  const r = await fetch("/api/delete_crew", {{
    method: "POST", headers: {{"Content-Type":"application/json"}},
    body: JSON.stringify({{id}}),
  }});
  const d = await r.json();
  if (d.ok) {{ showToast("Удалена"); setTimeout(()=>location.reload(), 300); }}
  else showToast(d.error || "Ошибка", true);
}}
</script>
</body></html>
"""


def _rating_pill_class(rating: int) -> str:
    if rating >= 4:
        return "early"
    if rating == 3:
        return "late"
    return "very-late"


def _compat_cell_class(score: int) -> str:
    if score <= -2:
        return "cc-2"
    if score == -1:
        return "cc-1"
    if score == 0:
        return "cc0"
    if score == 1:
        return "cc1"
    return "cc2"


def _skill_chips(rated: list, skill_by_id: dict, worker_id: int) -> str:
    if not rated:
        return '<span class="text-sm-muted">—</span>'
    return " ".join(
        f'<span class="skill-chip pill {_rating_pill_class(r["rating"])}" '
        f'onclick="openSkillModal({worker_id}, {r["skill_id"]})" '
        f'title="{html.escape(r["note"] or "")}">'
        f'{html.escape(skill_by_id.get(r["skill_id"], "?"))}: {r["rating"]}</span>'
        for r in rated
    )


def render_crews(user: str) -> str:
    workers = get_workers(include_deleted=False)
    worker_ids = [w["id"] for w in workers]
    skills = get_all_skills()
    worker_skills_map = get_worker_skills_map(worker_ids)
    compat_matrix = get_compat_matrix(worker_ids)
    crews = get_crews()
    crew_member_counts = count_workers_per_crew()

    skill_by_id = {s["id"]: s["name"] for s in skills}
    skill_kind_by_id = {s["id"]: s["kind"] for s in skills}
    skills_of_kind = {"skill": [s for s in skills if s["kind"] != "trait"],
                       "trait": [s for s in skills if s["kind"] == "trait"]}

    def catalog_chips(kind_list):
        if not kind_list:
            return '<span class="text-sm-muted">Пока пусто — добавь ниже.</span>'
        return "\n".join(
            f'<span class="skill-chip pill">'
            f'{html.escape(s["name"])} '
            f'<span class="skill-chip-x" onclick="deleteSkillFromCatalog({s["id"]}, '
            f'{html.escape(json.dumps(s["name"], ensure_ascii=False), quote=True)})">×</span>'
            f'</span>'
            for s in kind_list
        )

    worker_skill_rows = []
    for w in workers:
        rated = worker_skills_map.get(w["id"], [])
        rated_skill = [r for r in rated if skill_kind_by_id.get(r["skill_id"]) == "skill"]
        rated_trait = [r for r in rated if skill_kind_by_id.get(r["skill_id"]) == "trait"]
        worker_skill_rows.append(
            f'<tr><td><a href="/worker?id={w["id"]}">{html.escape(w["name"])}</a></td>'
            f'<td>{_skill_chips(rated_skill, skill_by_id, w["id"])}</td>'
            f'<td>{_skill_chips(rated_trait, skill_by_id, w["id"])}</td>'
            f'<td><button class="btn btn-sm" onclick="openSkillModal({w["id"]})">'
            f'⭐ Оценить</button></td></tr>'
        )
    worker_skill_rows_html = "\n".join(worker_skill_rows) if worker_skill_rows else \
        '<tr><td colspan="4" class="empty-cell">Нет сотрудников</td></tr>'

    compat_head = "".join(
        f'<th class="compat-col-head" title="{html.escape(w["name"])}">{html.escape(w["name"])}</th>'
        for w in workers
    )
    compat_rows = []
    for wf in workers:
        cells = []
        for wt in workers:
            if wf["id"] == wt["id"]:
                cells.append('<td class="compat-cell compat-diag">—</td>')
                continue
            entry = compat_matrix.get((wf["id"], wt["id"]))
            score = entry[0] if entry else None
            label = "" if score is None else (f"+{score}" if score > 0 else str(score))
            cls = _compat_cell_class(score) if score is not None else ""
            from_name_js = html.escape(json.dumps(wf["name"], ensure_ascii=False), quote=True)
            to_name_js = html.escape(json.dumps(wt["name"], ensure_ascii=False), quote=True)
            cells.append(
                f'<td class="compat-cell {cls}" '
                f'onclick="openCompatModal({wf["id"]}, {from_name_js}, {wt["id"]}, {to_name_js})">'
                f'{label}</td>'
            )
        compat_rows.append(
            f'<tr><th class="compat-row-head" title="{html.escape(wf["name"])}">{html.escape(wf["name"])}</th>'
            f'{"".join(cells)}</tr>'
        )
    compat_rows_html = "\n".join(compat_rows) if compat_rows else \
        '<tr><td class="empty-cell">Нет сотрудников</td></tr>'

    compat_json = {f"{f}_{t}": [score, note] for (f, t), (score, note) in compat_matrix.items()}

    crew_rows = []
    for cr in crews:
        cnt = crew_member_counts.get(cr["id"], 0)
        note_txt = html.escape(cr["note"]) if cr["note"] else '<span class="text-sm-muted">—</span>'
        name_for_js = html.escape(json.dumps(cr["name"], ensure_ascii=False), quote=True)
        crew_rows.append(
            f'<tr><td><a href="/crew?id={cr["id"]}">{html.escape(cr["name"])}</a></td>'
            f'<td>{note_txt}</td>'
            f'<td>{cnt}</td>'
            f'<td><a class="btn btn-sm" href="/crew?id={cr["id"]}">👥 Открыть</a>&nbsp;'
            f'<button class="btn btn-sm btn-danger" '
            f'onclick="deleteCrewFromList({cr["id"]}, {name_for_js})">Удалить</button></td></tr>'
        )
    crew_rows_html = "\n".join(crew_rows) if crew_rows else \
        '<tr><td colspan="4" class="empty-cell">Бригад пока нет. Нажми «➕ Создать бригаду»</td></tr>'

    return _CREWS_PAGE.format(
        topbar=topbar("crews", user),
        skill_catalog_chips_skill=catalog_chips(skills_of_kind["skill"]),
        skill_catalog_chips_trait=catalog_chips(skills_of_kind["trait"]),
        worker_skill_rows=worker_skill_rows_html,
        compat_head=compat_head,
        compat_rows=compat_rows_html,
        crew_rows=crew_rows_html,
        crew_count=len(crews),
        worker_count=len(workers),
        skills_json=json.dumps(
            [{"id": s["id"], "name": s["name"], "kind": s["kind"]} for s in skills], ensure_ascii=False
        ),
        worker_skills_json=json.dumps(worker_skills_map, ensure_ascii=False),
        compat_json=json.dumps(compat_json, ensure_ascii=False),
        compat_workers_json=json.dumps(
            [{"id": w["id"], "name": w["name"]} for w in workers], ensure_ascii=False
        ),
    )
