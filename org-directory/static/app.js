const $ = (sel, el = document) => el.querySelector(sel);
const app = $("#app");
const banner = $("#banner");

let currentUser = null;

const TOKEN_KEY = "hnwms_token";
function getToken() {
  try {
    return window.__HNWMS_TOKEN || sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || "";
  } catch (_) {
    return window.__HNWMS_TOKEN || "";
  }
}
function setToken(t) {
  window.__HNWMS_TOKEN = t || "";
  try {
    if (t) {
      sessionStorage.setItem(TOKEN_KEY, t);
      localStorage.setItem(TOKEN_KEY, t);
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (_) {}
}
function withToken(path) {
  const t = getToken();
  if (!t) return path;
  return path + (path.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(t);
}
const authHeaders = () => {
  const t = getToken();
  return t ? { Authorization: "Bearer " + t, "X-Session-Token": t } : {};
};

const api = (path, opts = {}) => {
  const headers = { ...(opts.headers || {}), ...authHeaders() };
  return fetch(withToken(path), { credentials: "include", ...opts, headers }).then(async (r) => {
    if (r.status === 401 && path.indexOf("/api/auth/login") === -1) {
      currentUser = null;
      setToken("");
      const err = new Error("login required");
      err.auth = true;
      throw err;
    }
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw Object.assign(new Error(data.error || path + " " + r.status), { data, status: r.status });
    return data;
  });
};
const apiPost = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const chip = (text, cls = "") => `<span class="chip ${cls}">${esc(text || "")}</span>`;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function navTo(view) {
  document.querySelectorAll(".nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  location.hash = view;
  const fn = views[view] || views.overview;
  fn();
}

document.querySelectorAll(".nav button[data-view]").forEach((b) => {
  b.addEventListener("click", () => navTo(b.dataset.view));
});
$("#logout")?.addEventListener("click", async () => {
  try { await apiPost("/api/auth/logout", {}); } catch (_) {}
  currentUser = null;
  setToken("");
  location.hash = "";
  showLogin();
});

function renderWho() {
  const el = $("#who");
  if (!el || !currentUser) return;
  el.innerHTML = `<strong>${esc(currentUser.display_name)}</strong><br>${esc(currentUser.job_title)}<br><code>${esc(currentUser.username)}</code>`;
}

function showLogin() {
  setToken("");
  currentUser = null;
  document.body.classList.add("guest");
  const gate = document.getElementById("gate");
  if (gate) gate.style.display = "";
}

async function afterLogin() {
  const me = await api("/api/auth/me");
  currentUser = me.user;
  document.body.classList.remove("guest");
  const gate = document.getElementById("gate");
  if (gate) gate.style.display = "none";
  renderWho();
  const s = await api("/api/summary");
  banner.innerHTML = `<strong>${esc(s.signoff)}</strong> · RBAC ${esc(s.rbac || "")} · Physical audit ${esc(s.walk_status)} · ${esc(s.warning)}`;
  const view = (location.hash || "#profile").slice(1) || "profile";
  navTo(view === "login" ? "profile" : view);
}

async function boot() {
  if (!getToken()) {
    showLogin();
    return;
  }
  try {
    await afterLogin();
  } catch (_) {
    showLogin();
  }
}
window.hnwmsBoot = boot;

const views = {
  async overview() {
    const [s, roll, depts] = await Promise.all([api("/api/summary"), api("/api/rollup"), api("/api/departments")]);
    app.innerHTML = `
      <h1>Registry overview</h1>
      <p class="sub">${esc(s.facility.name)} · ${esc(s.facility.city)} · licensor ${esc(s.facility.licensor)}</p>
      <div class="kpis">
        <div class="kpi"><span>Units</span><b>${s.units}</b></div>
        <div class="kpi"><span>Licensed inpatient</span><b>${s.licensed_inpatient}</b></div>
        <div class="kpi"><span>If ICU-EXT-2 merged</span><b>${s.licensed_inpatient_if_merged}</b></div>
        <div class="kpi"><span>ED stretchers</span><b>${s.ed_stretchers}</b></div>
      </div>
      <p class="muted">Source Bed sum ${s.source_bed_count} is history only. Pending DQ: ${s.pending_dq.map(esc).join(", ") || "none"}.</p>
      <div class="grid-2">
        <div class="panel">
          <h3>Capacity class</h3>
          <table><thead><tr><th>Class</th><th>Units</th><th>Resource</th><th>Licensed</th></tr></thead>
          <tbody>${roll.map((r) => `<tr><td>${chip(r.capacity_class)}</td><td>${r.unit_count}</td><td>${r.resource_capacity}</td><td>${r.licensed_capacity}</td></tr>`).join("")}</tbody></table>
        </div>
        <div class="panel">
          <h3>Departments</h3>
          <table><thead><tr><th>Code</th><th>Name</th><th>Units</th><th>Inpatient</th></tr></thead>
          <tbody>${depts.map((d) => `<tr><td><code>${esc(d.department_code)}</code></td><td>${esc(d.name)}</td><td>${d.unit_count}</td><td>${d.licensed_capacity}</td></tr>`).join("")}</tbody></table>
        </div>
      </div>`;
  },

  async units() {
    const units = await api("/api/units");
    app.innerHTML = `
      <h1>Units &amp; capacity</h1>
      <p class="sub">43 locations from the classed seed. Click a row for detail.</p>
      <div class="toolbar">
        <input id="q" placeholder="Search code or name" />
        <select id="cls"><option value="">All classes</option></select>
        <select id="dept"><option value="">All departments</option></select>
      </div>
      <div id="table"></div>`;
    const classes = [...new Set(units.map((u) => u.capacity_class))];
    const depts = [...new Set(units.map((u) => u.department_code))];
    classes.forEach((c) => $("#cls").insertAdjacentHTML("beforeend", `<option>${esc(c)}</option>`));
    depts.forEach((c) => $("#dept").insertAdjacentHTML("beforeend", `<option>${esc(c)}</option>`));
    const draw = () => {
      const q = $("#q").value.toLowerCase();
      const cls = $("#cls").value;
      const dept = $("#dept").value;
      const rows = units.filter((u) => {
        if (cls && u.capacity_class !== cls) return false;
        if (dept && u.department_code !== dept) return false;
        const hay = (u.unit_code + u.unit_name + u.department_name).toLowerCase();
        return !q || hay.includes(q);
      });
      $("#table").innerHTML = `<table><thead><tr>
        <th>Code</th><th>Unit</th><th>Dept</th><th>Class</th><th>Licensed</th><th>Resource</th><th>Walk</th><th>DQ</th>
      </tr></thead><tbody>${rows.map((u) => `<tr class="clickable" data-code="${esc(u.unit_code)}">
        <td><code>${esc(u.unit_code)}</code></td>
        <td>${esc(u.unit_name)}</td>
        <td>${esc(u.department_code)}</td>
        <td>${chip(u.capacity_class)}</td>
        <td>${u.licensed_capacity}</td>
        <td>${u.resource_capacity}</td>
        <td>${chip(u.walk_status, "warn")}</td>
        <td>${u.dq_flag ? chip(u.dq_flag, "gold") : ""}</td>
      </tr>`).join("")}</tbody></table>`;
      $("#table").querySelectorAll("tr.clickable").forEach((tr) => {
        tr.addEventListener("click", () => showUnit(tr.dataset.code));
      });
    };
    $("#q").addEventListener("input", draw);
    $("#cls").addEventListener("change", draw);
    $("#dept").addEventListener("change", draw);
    draw();
  },

  async org() {
    const treeData = await api("/api/org-tree");
    const render = (nodes) => `<ul>${nodes.map((n) => `<li><div class="node">${esc(n.name)} <small>${esc(n.org_code)} · ${esc(n.node_type)}</small></div>${n.children?.length ? render(n.children) : ""}</li>`).join("")}</ul>`;
    app.innerHTML = `<h1>Workforce org tree</h1>
      <p class="sub">From Hospital_Nursing_Organizational_Structure.md. Reporting line, not bed capacity.</p>
      <div class="tree panel">${render(treeData)}</div>`;
  },

  async positions() {
    const pos = await api("/api/positions");
    app.innerHTML = `<h1>Position catalogue</h1>
      <p class="sub">E1–E2 executive and L1–L7 nursing. No people loaded (Staff Master is empty on purpose).</p>
      <table><thead><tr><th>Level</th><th>Code</th><th>Title</th><th>Org node</th></tr></thead>
      <tbody>${pos.map((p) => `<tr><td>${chip(p.position_level)}</td><td><code>${esc(p.position_code)}</code></td><td>${esc(p.title)}</td><td>${esc(p.org_name)}</td></tr>`).join("")}</tbody></table>`;
  },

  async coverage() {
    const cov = await api("/api/coverage");
    const lines = {};
    cov.forEach((c) => { (lines[c.clinical_line] ||= []).push(c); });
    app.innerHTML = `<h1>Coverage map (proposed)</h1>
      <p class="sub">DQ-14: Nursing Operations clinical lines scoped to units. Status PROPOSED until DON signs.</p>
      ${Object.entries(lines).map(([line, items]) => `
        <div class="panel" style="margin-bottom:14px">
          <h3>${esc(line)}</h3>
          <p>${items.map((i) => `<code>${esc(i.unit_code)}</code>`).join(" ")}</p>
        </div>`).join("")}`;
  },

  async profile() {
    const data = await api("/api/um/profile");
    const p = data.profile;
    const fields = [
      ["mobile", "Mobile"],
      ["national_id", "National ID / Iqama"],
      ["nationality", "Nationality"],
      ["gender", "Gender"],
      ["date_of_birth", "Date of birth"],
      ["scfhs_no", "SCFHS number"],
      ["license_no", "License number"],
      ["license_authority", "License authority"],
      ["license_expiry", "License expiry"],
      ["employment_type", "Employment type"],
      ["fte", "FTE"],
      ["hire_date", "Hire date"],
      ["emergency_name", "Emergency contact"],
      ["emergency_phone", "Emergency phone"],
    ];
    const latest = {};
    data.documents.forEach((d) => { latest[d.doc_code] = d; });
    app.innerHTML = `
      <h1>My profile</h1>
      <p class="sub">${esc(data.persona.display_name)} · ${esc(data.persona.job_title)}
        · ${data.complete ? chip("Complete", "ok") : chip("Incomplete", "warn")}</p>
      <div class="panel" style="margin-bottom:16px">
        <h3>Staff data</h3>
        <p class="muted">Fill the fields the system recommends. Save before uploading files.</p>
        <div class="form-grid" id="pf">
          ${fields.map(([k, lab]) => `<label class="muted">${esc(lab)}</label><input data-k="${k}" value="${esc(p[k] || "")}" />`).join("")}
          <label class="muted">New password (optional)</label><input data-k="new_password" type="password" placeholder="Leave blank to keep" />
        </div>
        <p style="margin-top:14px"><button type="button" class="save" id="save-profile">Save profile</button> <span id="ps" class="muted"></span></p>
      </div>
      <div class="panel">
        <h3>Recommended files</h3>
        <p class="muted">Mandatory documents must be attached. PDF, JPG, PNG, WEBP, DOC — max 8 MB.</p>
        ${data.doc_types.map((t) => {
          const d = latest[t.doc_code];
          return `<div class="doc-row">
            <div><strong>${esc(t.label)}</strong> ${chip(t.category, t.category === "MANDATORY" ? "warn" : t.category === "REQUIRED" ? "gold" : "")}
              <div class="muted">${esc(t.notes)}</div>
              ${d ? `<div>${chip("Attached", "ok")} <a href="${withToken("/api/um/documents/" + d.document_id)}">${esc(d.original_name)}</a></div>` : chip("Missing", "warn")}
            </div>
            <div><input type="file" data-doc="${esc(t.doc_code)}" /></div>
          </div>`;
        }).join("")}
        <p class="muted" id="up-msg"></p>
      </div>`;
    $("#save-profile").addEventListener("click", async () => {
      const body = { persona: data.persona.persona_code };
      $("#pf").querySelectorAll("input").forEach((i) => { body[i.dataset.k] = i.value; });
      try {
        const res = await apiPost("/api/um/profile", body);
        $("#ps").textContent = res.complete ? "Saved — profile complete" : "Saved — still missing recommended items";
      } catch (e) {
        $("#ps").textContent = e.message;
      }
    });
    app.querySelectorAll("input[type=file]").forEach((inp) => {
      inp.addEventListener("change", async () => {
        if (!inp.files?.[0]) return;
        const fd = new FormData();
        fd.append("doc_code", inp.dataset.doc);
        fd.append("persona", data.persona.persona_code);
        fd.append("file", inp.files[0]);
        $("#up-msg").textContent = "Uploading…";
        try {
          const r = await fetch(withToken("/api/um/documents"), { method: "POST", body: fd, credentials: "include", headers: authHeaders() });
          const res = await r.json();
          if (!r.ok) throw new Error(res.error || "upload failed");
          $("#up-msg").textContent = "Uploaded.";
          views.profile();
        } catch (e) {
          $("#up-msg").textContent = e.message;
        }
      });
    });
  },

  async people() {
    const people = await api("/api/rbac/people");
    const cats = [...new Set(people.map((p) => p.category || "Other"))];
    app.innerHTML = `
      <h1>People — system-user slots</h1>
      <p class="sub">Every login HNWMS needs. <strong>Not Staff Master</strong> (no full nurse roster). Slot code stays; rename to the real employee. Staff sign in on My profile to complete data and attach files.</p>
      <div class="toolbar">
        <input id="q" placeholder="Search name, title, or slot" />
        <select id="cat"><option value="">All groups</option>${cats.map((c) => `<option>${esc(c)}</option>`).join("")}</select>
      </div>
      <p class="muted" id="count"></p>
      <div id="table"></div>`;
    const draw = () => {
      const q = $("#q").value.toLowerCase();
      const cat = $("#cat").value;
      const rows = people.filter((p) => {
        if (cat && p.category !== cat) return false;
        const hay = [p.display_name, p.job_title, p.persona_code, p.notes].join(" ").toLowerCase();
        return !q || hay.includes(q);
      });
      $("#count").textContent = `${rows.length} of ${people.length} slots`;
      $("#table").innerHTML = `<table><thead><tr>
        <th>Group</th><th>Slot (stable)</th><th>Person (rename later)</th><th>Job</th><th>Grants</th><th></th>
      </tr></thead><tbody>${rows.map((p) => `<tr>
        <td>${chip(p.category)}</td>
        <td><code>${esc(p.persona_code)}</code></td>
        <td><input class="name-in" data-code="${esc(p.persona_code)}" value="${esc(p.display_name)}" /></td>
        <td>${esc(p.job_title)}</td>
        <td>${p.grants.map((g) => chip(`${g.role} @ ${g.scope_code}`)).join(" ")}</td>
        <td><button type="button" class="save" data-code="${esc(p.persona_code)}">Save</button></td>
      </tr>`).join("")}</tbody></table>`;
      $("#table").querySelectorAll("button.save").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const code = btn.dataset.code;
          const input = btn.closest("tr").querySelector("input.name-in");
          const res = await apiPost("/api/rbac/people/rename", { persona_code: code, display_name: input.value });
          if (res.ok) {
            const p = people.find((x) => x.persona_code === code);
            if (p) p.display_name = res.display_name;
            btn.textContent = "Saved";
            setTimeout(() => { btn.textContent = "Save"; }, 1200);
          }
        });
      });
    };
    $("#q").addEventListener("input", draw);
    $("#cat").addEventListener("change", draw);
    draw();
  },

  async rbac() {
    const [roles, matrix, grants, sod, scenarios, units, people] = await Promise.all([
      api("/api/roles"),
      api("/api/rbac/matrix"),
      api("/api/rbac/grants"),
      api("/api/rbac/sod"),
      api("/api/rbac/scenarios"),
      api("/api/units"),
      api("/api/rbac/people"),
    ]);
    const permList = [...new Set(matrix.permissions.map((p) => p.perm_code))];
    const grouped = {};
    people.forEach((p) => { (grouped[p.category || "Other"] ||= []).push(p); });
    const peopleOpts = Object.entries(grouped).map(([cat, list]) =>
      `<optgroup label="${esc(cat)}">${list.map((p) => `<option value="${esc(p.persona_code)}">${esc(p.display_name)} — ${esc(p.job_title)}</option>`).join("")}</optgroup>`
    ).join("");
    app.innerHTML = `
      <h1>RBAC module — applied</h1>
      <p class="sub">Approved 2026-09-09. Engine is live. People are demo slots (rename on People; needs ORG_WRITE). Hard rule: bed control ≠ scheduling. Charge is unit-scoped.</p>

      <div class="panel" style="margin-bottom:16px">
        <h3>Try a decision</h3>
        <div class="toolbar">
          <select id="sub">${peopleOpts}</select>
          <select id="perm">${permList.map((p) => `<option ${p === "BED_CONTROL" ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>
          <select id="res">${units.map((u) => `<option value="${esc(u.unit_code)}">${esc(u.unit_code)} — ${esc(u.unit_name)}</option>`).join("")}</select>
          <button type="button" id="go">Evaluate</button>
        </div>
        <div id="verdict" class="muted">Pick a persona, permission, and unit.</div>
      </div>

      <h3>Canned cases (expected)</h3>
      <table style="margin-bottom:18px"><thead><tr><th>Who</th><th>Permission</th><th>Resource</th><th>Result</th><th>Why</th></tr></thead>
      <tbody>${scenarios.map((s) => `<tr>
        <td><code>${esc(s.subject)}</code></td>
        <td>${esc(s.permission)}</td>
        <td>${esc(s.resource.code)}</td>
        <td>${s.allow ? chip("ALLOW") : chip("DENY", "warn")}</td>
        <td class="muted">${esc(s.reason)}</td>
      </tr>`).join("")}</tbody></table>

      <h3>Demo grants</h3>
      <table style="margin-bottom:18px"><thead><tr><th>Persona</th><th>Role</th><th>Scope</th></tr></thead>
      <tbody>${grants.map((g) => `<tr>
        <td>${esc(g.display_name)}<br><code>${esc(g.persona_code)}</code></td>
        <td>${esc(g.role_code)}</td>
        <td>${chip(g.scope_type)} <code>${esc(g.scope_code)}</code></td>
      </tr>`).join("")}</tbody></table>

      <h3>SoD</h3>
      <p>${sod.map((r) => chip(`${r.perm_a} × ${r.perm_b}`, "warn") + " " + esc(r.message) + ` (waive: ${esc(r.waive_roles)})`).join("<br>")}</p>

      <h3>Role × permission matrix</h3>
      <div style="overflow:auto">
      <table><thead><tr><th>Role</th>${matrix.permissions.map((p) => `<th>${esc(p.perm_code)}</th>`).join("")}</tr></thead>
      <tbody>${matrix.roles.map((role) => `<tr>
        <td>${esc(role.role_code)}</td>
        ${matrix.permissions.map((p) => {
          const on = matrix.cells.find((c) => c.role === role.role_code && c.permission === p.perm_code)?.granted;
          return `<td>${on ? "●" : ""}</td>`;
        }).join("")}
      </tr>`).join("")}</tbody></table>
      </div>

      <h3>Role catalogue</h3>
      <table><thead><tr><th>Role</th><th>Default scope</th><th>Permissions</th></tr></thead>
      <tbody>${roles.map((r) => `<tr><td>${esc(r.title)}<br><code>${esc(r.role_code)}</code></td>
        <td>${chip(r.data_scope)}</td>
        <td>${r.permissions.map((p) => chip(p, p === "BED_CONTROL" ? "gold" : p === "SCHED_WRITE" ? "warn" : "")).join(" ")}</td>
      </tr>`).join("")}</tbody></table>
      <p class="muted">Contract: <code>rbac/README.md</code> · engine: <code>rbac/engine.py</code>. ADT / Scheduling / HNWMS must call <code>/api/rbac/evaluate</code> before bed control or roster publish.</p>`;

    $("#go").addEventListener("click", async () => {
      const q = new URLSearchParams({
        subject: $("#sub").value,
        permission: $("#perm").value,
        resource_type: "UNIT",
        resource_code: $("#res").value,
      });
      const res = await api("/api/rbac/evaluate?" + q.toString());
      $("#verdict").innerHTML = res.allow
        ? chip("ALLOW") + " " + esc(res.reason)
        : chip("DENY", "warn") + " " + esc(res.reason);
    });
  },

  async audit() {
    const rows = await api("/api/audit");
    app.innerHTML = `<h1>Desk audit</h1>
      <p class="sub">Not a floor walk. Print 08_signoff_don_licensing.md and physical_bed_audit_unit_sheets.csv for the site visit.</p>
      <table><thead><tr><th>Unit</th><th>Walk</th><th>Exists</th><th>Recommendation</th><th>Notes</th></tr></thead>
      <tbody>${rows.map((a) => `<tr>
        <td><code>${esc(a.unit_code)}</code></td>
        <td>${chip(a.walk_status, "warn")}</td>
        <td>${esc(a.physical_exists)}</td>
        <td>${chip(a.desk_recommendation, "gold")}</td>
        <td class="muted">${esc(a.notes)}</td>
      </tr>`).join("")}</tbody></table>`;
  },

  async api() {
    const paths = [
      "/api/health", "/api/summary", "/api/facilities", "/api/departments", "/api/unit-groups",
      "/api/units", "/api/units/W3A", "/api/org-tree", "/api/positions", "/api/coverage",
      "/api/roles", "/api/rbac/me", "/api/rbac/people", "/api/rbac/matrix", "/api/rbac/scenarios", "/api/rbac/evaluate",
      "/api/vocabulary", "/api/audit", "/api/rollup", "/api/events",
    ];
    app.innerHTML = `<h1>Consumer APIs</h1>
      <p class="sub">Location master for ADT, Scheduling, HNWMS, Payroll. Relative URLs only.</p>
      <div class="panel api-list">${paths.map((p) => `<div><a href="${p}" target="_blank" rel="noopener"><code>${p}</code></a></div>`).join("")}</div>`;
  },
};

async function showUnit(code) {
  const u = await api("/api/units/" + encodeURIComponent(code));
  app.innerHTML = `
    <p><button id="back">← All units</button></p>
    <h1>${esc(u.unit_name)}</h1>
    <p class="sub"><code>${esc(u.unit_code)}</code> · ${esc(u.department_name)}</p>
    <div class="panel detail-grid">
      ${[
        ["Unit type", u.unit_type],
        ["Care setting", u.care_setting],
        ["Capacity class", u.capacity_class],
        ["Group", u.unit_group_name],
        ["Source Bed", u.source_bed_count ?? "—"],
        ["Resource capacity", u.resource_capacity],
        ["Licensed inpatient", u.licensed_capacity],
        ["Patient-placeable", u.is_bedded ? "yes" : "no"],
        ["DQ flag", u.dq_flag || "—"],
        ["Walk status", u.walk_status],
        ["Desk recommendation", u.desk_recommendation],
        ["Notes", u.audit_notes],
      ].map(([k, v]) => `<div class="muted">${esc(k)}</div><div>${esc(v)}</div>`).join("")}
    </div>`;
  $("#back").addEventListener("click", () => navTo("units"));
}

boot();
