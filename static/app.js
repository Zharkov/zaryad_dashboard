function showToast(msg, isError) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => t.classList.remove("show"), 2500);
}

function switchTab(name, btn) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("tab_" + name).classList.add("active");
}

function makeAjaxSearch(endpoint, bodyId, totalId) {
  let timer = null;
  let seq = 0;
  async function run(val) {
    const mySeq = ++seq;
    const u = new URL(location.href);
    if (val) u.searchParams.set("search", val);
    else u.searchParams.delete("search");
    history.replaceState(null, "", u.toString());
    try {
      const r = await fetch(endpoint + "?search=" + encodeURIComponent(val));
      const d = await r.json();
      if (mySeq !== seq) return;
      if (d.ok) {
        document.getElementById(bodyId).innerHTML = d.rows;
        document.getElementById(totalId).textContent = d.total;
      }
    } catch (e) {}
  }
  return function(val) {
    clearTimeout(timer);
    timer = setTimeout(() => run(val), 300);
  };
}
