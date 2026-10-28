/* getcontact web app — vanilla JS over the Apollo-compatible API at /api/v1 */
const API = "/api/v1";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => (n ?? 0).toLocaleString();
const day = (d) => (d ? String(d).slice(0, 10) : "—");
const when = (d) => (d ? String(d).slice(0, 16).replace("T", " ") : "—");

const views = {};
const state = {
  user: null, credits: null, revealed: {}, sel: new Set(), bulk: null,
  p: { filters: {}, page: 1, tab: "all" }, c: { filters: {}, page: 1, tab: "all" },
};

/* ---------- icons (24px stroke) ---------- */
const P = {
  home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  people: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 010 7M18 14.6c2 .7 3.2 2.5 3.5 5.4"/>',
  building: '<path d="M4 21V5l8-2v18"/><path d="M12 9h8v12"/><path d="M7 8h2M7 12h2M7 16h2M15 13h2M15 17h2M2 21h20"/>',
  contact: '<circle cx="10" cy="8" r="4"/><path d="M3 20c.7-3.7 3.4-6 7-6 1.5 0 2.9.4 4 1.1"/><path d="M16 18l2 2 4-4"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  send: '<path d="M21 3L10 14"/><path d="M21 3l-7 18-4-7-7-4z"/>',
  bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  share: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="5.5" r="2.5"/><circle cx="18" cy="18.5" r="2.5"/><path d="M8.2 10.8l7.6-4.1M8.2 13.2l7.6 4.1"/>',
  radar: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12l6-6"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  chev: '<path d="M6 9l6 6 6-6"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  check: '<path d="M5 12l5 5L20 7"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h8"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  phone: '<path d="M5 3h4l2 5-2.5 1.5a11 11 0 006 6L16 13l5 2v4a2 2 0 01-2 2A16 16 0 013 5a2 2 0 012-2"/>',
  pin: '<path d="M12 21s7-6 7-12a7 7 0 00-14 0c0 6 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  brief: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 13h18"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
  tag: '<path d="M3 12V4a1 1 0 011-1h8l9 9-9 9z"/><circle cx="8" cy="8" r="1.5"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  minus: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
  filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c.8-4 4-6.5 8-6.5s7.2 2.5 8 6.5"/>',
  factory: '<path d="M3 21V10l6 3V10l6 3V6l6 3v12z"/>',
  back: '<path d="M15 6l-6 6 6 6"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>',
  play: '<path d="M7 4l13 8-13 8z"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  upload: '<path d="M12 21V9M7 14l5-5 5 5M4 3h16"/>',
};
const icon = (n, cls = "") => `<span class="ico ${cls}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${P[n] || ""}</svg></span>`;

/* ---------- labels ---------- */
const SENIORITIES = [["owner", "Owner"], ["founder", "Founder"], ["c_suite", "C-suite"], ["partner", "Partner"], ["vp", "VP"], ["head", "Head"], ["director", "Director"], ["manager", "Manager"], ["senior", "Senior"], ["entry", "Entry"]];
const DEPARTMENTS = [["executive", "Executive"], ["engineering", "Engineering"], ["sales", "Sales"], ["marketing", "Marketing"], ["finance", "Finance"], ["operations", "Operations"], ["hr", "HR"], ["legal", "Legal"], ["product", "Product"], ["it", "IT & data"]];
const EMP = [["1,10", "1–10"], ["11,50", "11–50"], ["51,200", "51–200"], ["201,500", "201–500"], ["501,1000", "501–1,000"], ["1001,5000", "1,001–5,000"], ["5001,10000", "5,001–10,000"], ["10001,", "10,000+"]];
const EMAIL_ST = [["verified", "Verified"], ["mx_valid", "Likely valid"], ["guessed", "Pattern guess"]];
const STATUS = { verified: "Verified", mx_valid: "Likely valid", guessed: "Pattern guess", invalid: "Bounced", suppressed: "Opted out", guessable: "Available", unavailable: "Unavailable", none: "Unavailable" };
const SRC = { sec_insiders: "SEC insider", sec_formd: "SEC Form D", sec_edgar: "SEC", wikidata: "Wikidata", gleif: "GLEIF", companies_house: "Companies House", tranco: "Web domain", contributor: "Contributed", imap: "Contributed", mbox: "Contributed", eml: "Contributed", csv: "Contributed", hubspot: "Contributed", auto_reply: "Contributed", webcrawl: "Company site", hunter: "Hunter", user: "Added by you", opencorporates: "OpenCorporates", data_gov_in: "MCA India", apollo: "Apollo" };
const PERSON_SOURCES = [["sec_insiders", "SEC insider filings"], ["sec_formd", "SEC Form D"], ["wikidata", "Wikidata"], ["companies_house", "Companies House"], ["webcrawl", "Company websites"], ["contributor", "Contributed (mail)"], ["csv", "Contributed (CSV)"], ["hunter", "Hunter"], ["user", "Added by you"]];
const ORG_SOURCES = [["sec_edgar", "SEC"], ["gleif", "GLEIF"], ["companies_house", "Companies House"], ["wikidata", "Wikidata"], ["tranco", "Web domains"], ["contributor", "Contributed"], ["data_gov_in", "MCA India"], ["opencorporates", "OpenCorporates"]];
const lbl = (pairs, v) => (pairs.find((p) => p[0] === v) || [v, v])[1];

/* ---------- api ---------- */
async function api(path, opts = {}) {
  const r = await fetch(API + path, { credentials: "same-origin", ...opts, headers: { ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}), ...(opts.headers || {}) } });
  if (r.status === 401) { showAuth(); throw new Error("Your session ended. Log in again."); }
  const ct = r.headers.get("content-type") || "";
  const body = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) {
    const d = body?.detail;
    const msg = typeof d === "string" ? d : d?.error ? d.error.replace(/_/g, " ") + (d.hint ? ` — ${d.hint}` : "") : r.statusText;
    toast(msg, true);
    throw new Error(msg);
  }
  return body;
}
const post = (p, b) => api(p, { method: "POST", body: b instanceof FormData ? b : JSON.stringify(b || {}) });
const del = (p) => api(p, { method: "DELETE" });
function qs(obj) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (Array.isArray(v)) v.forEach((x) => x !== "" && p.append(k + "[]", x));
    else if (v !== "" && v != null && v !== false) p.append(k, v);
  }
  return p.toString();
}
function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg; t.classList.toggle("err", err); t.classList.remove("hidden");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), 3800);
}

/* ---------- identity marks ---------- */
const hue = (s) => { let h = 0; for (const c of String(s || "?")) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
const initials = (n) => String(n || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((x) => x[0]).join("").toUpperCase();
const avatar = (name, lg) => `<span class="av${lg ? " lg" : ""}" style="background:hsl(${hue(name)} 34% 36%)" aria-hidden="true">${esc(initials(name))}</span>`;
const logo = (name, lg) => { const h = hue(name); return `<span class="logo${lg ? " lg" : ""}" style="background:hsl(${h} 40% 92%);color:hsl(${h} 45% 28%)" aria-hidden="true">${esc((String(name || "?").replace(/^the\s+/i, "")[0] || "?").toUpperCase())}</span>`; };
const loc = (x) => (x ? [x.city, x.state, x.country].filter(Boolean).join(", ") : "");
const liLink = (u) => (u ? `<a class="li" href="${esc(u)}" target="_blank" rel="noopener" title="Open LinkedIn profile">in</a>` : "");

/* ---------- dialogs ---------- */
function dialog({ title, body = "", fields = [], ok = "Save", danger = false }) {
  return new Promise((res) => {
    const wrap = document.createElement("div");
    wrap.className = "dlg-wrap";
    const field = (f) => {
      if (f.type === "select") return `<select name="${f.name}">${f.options.map((o) => `<option value="${esc(o[0])}" ${o[0] === f.value ? "selected" : ""}>${esc(o[1])}</option>`).join("")}</select>`;
      if (f.type === "textarea") return `<textarea name="${f.name}" placeholder="${esc(f.placeholder || "")}">${esc(f.value || "")}</textarea>`;
      if (f.type === "checkbox") return `<label class="check"><input type="checkbox" name="${f.name}" ${f.value ? "checked" : ""}> ${esc(f.text || "")}</label>`;
      return `<input name="${f.name}" type="${f.type || "text"}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}" ${f.list ? `list="dl-${f.name}"` : ""} ${f.required ? "required" : ""}>${f.list ? `<datalist id="dl-${f.name}">${f.list.map((o) => `<option value="${esc(o)}">`).join("")}</datalist>` : ""}`;
    };
    wrap.innerHTML = `<form class="dlg" role="dialog" aria-modal="true" aria-label="${esc(title)}"><h3>${esc(title)}</h3>${body ? `<p class="muted">${body}</p>` : ""}${fields.map((f) => `<div class="fld">${f.type === "checkbox" ? "" : `<span>${esc(f.label)}</span>`}${field(f)}</div>`).join("")}<div class="dlg-act"><button type="button" class="btn" data-x>Cancel</button><button class="btn ${danger ? "danger" : "primary"}">${esc(ok)}</button></div></form>`;
    document.body.append(wrap);
    const f = $("form", wrap);
    const close = (v) => { wrap.remove(); res(v); };
    $("[data-x]", wrap).onclick = () => close(null);
    wrap.onmousedown = (e) => { if (e.target === wrap) close(null); };
    wrap.onkeydown = (e) => { if (e.key === "Escape") close(null); };
    f.onsubmit = (e) => { e.preventDefault(); const o = {}; fields.forEach((fl) => { const el = f.elements[fl.name]; o[fl.name] = fl.type === "checkbox" ? el.checked : el.value.trim(); }); close(o); };
    (f.querySelector("input,select,textarea") || $(".btn:last-child", f)).focus();
  });
}
const confirmDlg = (title, body, ok = "Continue", danger = false) => dialog({ title, body, ok, danger }).then((r) => r !== null);

async function chooseList(kind = "people") {
  const { lists } = await api("/lists");
  const mine = lists.filter((l) => l.kind === kind);
  const r = await dialog({ title: "Add to list", body: mine.length ? "Pick a list or type a new name." : "Name your first list.", ok: "Add", fields: [{ name: "name", label: "List", list: mine.map((l) => l.name), required: true, placeholder: kind === "people" ? "e.g. Q4 fintech CFOs" : "e.g. Target accounts" }] });
  if (!r?.name) return null;
  const hit = mine.find((l) => l.name.toLowerCase() === r.name.toLowerCase());
  return hit ? hit.id : (await post("/lists", { name: r.name, kind })).list.id;
}
async function chooseSequence() {
  const { sequences } = await api("/sequences");
  const r = await dialog({ title: "Add to sequence", body: sequences.length ? "Pick a sequence or type a new name." : "Name your first sequence. You can add its steps next.", ok: "Add", fields: [{ name: "name", label: "Sequence", list: sequences.map((s) => s.name), required: true, placeholder: "e.g. Founder intro" }] });
  if (!r?.name) return null;
  const hit = sequences.find((s) => s.name.toLowerCase() === r.name.toLowerCase());
  return hit || (await post("/sequences", { name: r.name })).sequence;
}

/* ---------- email cell (signature) ---------- */
function emailHTML(p, animate = false) {
  const phone = (p.phone_numbers || [])[0]?.raw_number;
  return `<span class="email${animate ? " unmask" : ""}"><span class="dot st-${esc(p.email_status)}" title="${esc(STATUS[p.email_status] || p.email_status)}"></span><span class="addr">${esc(p.email)}</span><button class="copy" data-copy="${esc(p.email)}" aria-label="Copy ${esc(p.email)}">${icon("copy")}</button></span>${phone ? `<div class="sub mono">${esc(phone)}</div>` : ""}`;
}
function emailCell(p) {
  const r = state.revealed[p.id];
  if (r?.email) return emailHTML(r);
  if (r && !r.email) return `<span class="nomail">Not found</span>`;
  if (p.email) return emailHTML(p);
  if (!p.has_email) return `<span class="nomail">No company domain</span>`;
  return `<button class="reveal" data-reveal="${p.id}" aria-label="Access email for ${esc(p.name)} (1 credit)"><span class="bar"></span><span class="lbl">Access email</span></button>`;
}
async function revealPerson(id, phone = false) {
  $$(`[data-reveal="${id}"]`).forEach((b) => { b.classList.add("loading"); b.disabled = true; });
  try {
    const r = await post(`/people/match?${qs({ id, reveal_phone_number: phone })}`);
    const p = r.person || {};
    state.revealed[id] = p;
    $$(`[data-reveal="${id}"]`).forEach((b) => { b.outerHTML = p.email ? emailHTML(p, true) : `<span class="nomail">Not found</span>`; });
    refreshCredits();
    return p;
  } catch { $$(`[data-reveal="${id}"]`).forEach((b) => { b.classList.remove("loading"); b.disabled = false; }); }
}

/* ---------- selection + bulk bar ---------- */
function setBulk(kind, render) { state.bulk = { kind, render }; state.sel.clear(); updateBulk(); }
function updateBulk() {
  const bar = $("#bulkbar");
  if (!state.bulk || !state.sel.size) { bar.classList.add("hidden"); return; }
  bar.innerHTML = `<span class="n">${state.sel.size} selected</span>${state.bulk.render()}<button class="btn icon" data-bulk="clear" aria-label="Clear selection">${icon("x")}</button>`;
  bar.classList.remove("hidden");
  $$("tr[data-id]").forEach((tr) => tr.classList.toggle("sel", state.sel.has(+tr.dataset.id)));
}
async function savePeopleAsContacts(ids) {
  const out = [];
  for (const id of ids) out.push((await post("/contacts", { person_id: id })).contact.id);
  return out;
}
async function onBulk(action) {
  const ids = [...state.sel];
  if (action === "clear") { state.sel.clear(); $$("[data-sel]").forEach((c) => (c.checked = false)); $$("[data-selall]").forEach((c) => (c.checked = false)); return updateBulk(); }
  if (action === "reveal") {
    if (!(await confirmDlg("Access emails", `This uses up to ${ids.length} credit${ids.length > 1 ? "s" : ""}, one per email found. Each person is saved to Contacts.`, "Access emails"))) return;
    for (const id of ids) if (!state.revealed[id]) await revealPerson(id);
    toast(`Accessed ${ids.length} email${ids.length > 1 ? "s" : ""}`);
  }
  if (action === "save") { await savePeopleAsContacts(ids); toast(`Saved ${ids.length} to Contacts`); }
  if (action === "list") {
    const kind = state.bulk.kind === "companies" ? "companies" : "people";
    const l = await chooseList(kind); if (!l) return;
    const r = await post(`/lists/${l}/items`, kind === "people" ? { person_ids: ids } : { organization_ids: ids });
    toast(`Added ${r.added} to list`);
  }
  if (action === "sequence") {
    const s = await chooseSequence(); if (!s) return;
    const cids = state.bulk.kind === "contacts" ? ids : await savePeopleAsContacts(ids);
    const r = await post(`/sequences/${s.id}/enroll`, { contact_ids: cids });
    toast(`Added ${r.enrolled} to ${s.name}`);
  }
  if (action === "delete") {
    if (!(await confirmDlg("Remove contacts", `Remove ${ids.length} contact${ids.length > 1 ? "s" : ""} from your workspace? The library record stays.`, "Remove", true))) return;
    for (const id of ids) await del(`/contacts/${id}`);
    toast(`Removed ${ids.length}`); route();
  }
  onBulk("clear");
}

/* ---------- drawer ---------- */
function openDrawer(html) {
  const d = $("#drawer");
  d.innerHTML = html; d.classList.add("open"); d.setAttribute("aria-hidden", "false");
  if (!$(".scrim")) { const s = document.createElement("div"); s.className = "scrim"; s.onclick = closeDrawer; document.body.append(s); }
  $(".dr-close", d)?.focus();
}
function closeDrawer() {
  const d = $("#drawer");
  d.classList.remove("open"); d.setAttribute("aria-hidden", "true"); $(".scrim")?.remove();
}
async function personDrawer(id) {
  openDrawer(`<div class="dr-body"><div class="skel" style="margin-top:24px;width:60%"></div><div class="skel" style="margin-top:12px"></div></div>`);
  const { person: p, organization: o } = await api(`/people/${id}`);
  const r = state.revealed[id];
  openDrawer(`<div class="dr-head">${avatar(p.name, true)}<div><h2>${esc(p.name)}</h2><p>${esc(p.title || "Role not listed")}${o ? ` at <button class="linkish nm" data-open-company="${o.id}" style="border:0;background:none;padding:0;color:var(--teal);cursor:pointer">${esc(o.name)}</button>` : ""}</p><p class="faint" style="font-size:12px">${esc(loc(p) || loc(o))}</p></div><button class="btn icon ghost dr-close" data-close aria-label="Close">${icon("x")}</button></div>
  <div class="dr-actions">${r?.email || p.email ? "" : p.has_email ? `<button class="btn credit" data-dr="reveal">${icon("mail")} Access email · 1 credit</button>` : ""}<button class="btn" data-dr="save">${icon("contact")} Save</button><button class="btn" data-dr="list">${icon("list")} Add to list</button><button class="btn" data-dr="seq">${icon("send")} Add to sequence</button></div>
  <div class="dr-body">
    <section class="dr-sec"><h3>Contact</h3><dl class="kv"><dt>Email</dt><dd id="drEmail">${emailCell(p)}</dd><dt>Phone</dt><dd>${r?.phone_numbers?.length ? `<span class="mono">${esc(r.phone_numbers[0].raw_number)}</span>` : p.has_direct_phone ? `<button class="btn sm credit" data-dr="phone">${icon("phone")} Access phone · 8 credits</button>` : '<span class="faint">Not available</span>'}</dd><dt>LinkedIn</dt><dd>${p.linkedin_url ? `<a href="${esc(p.linkedin_url)}" target="_blank" rel="noopener">${esc(p.linkedin_url.replace(/^https?:\/\/(www\.)?/, ""))}</a>` : '<span class="faint">Not linked</span>'}</dd></dl></section>
    <section class="dr-sec"><h3>Role</h3><dl class="kv"><dt>Title</dt><dd>${esc(p.title || "—")}</dd><dt>Seniority</dt><dd>${esc(lbl(SENIORITIES, p.seniority) || "—")}</dd><dt>Department</dt><dd>${esc(lbl(DEPARTMENTS, p.department) || "—")}</dd><dt>Location</dt><dd>${esc(loc(p) || "—")}</dd></dl></section>
    ${o ? `<section class="dr-sec"><h3>Company</h3><div class="co" style="margin-bottom:10px">${logo(o.name)}<div><button class="nm" data-open-company="${o.id}">${esc(o.name)}</button><div class="sub">${o.domain ? `<a href="https://${esc(o.domain)}" target="_blank" rel="noopener">${esc(o.domain)}</a>` : "No website on file"}</div></div></div><dl class="kv"><dt>Industry</dt><dd>${esc(o.industry || "—")}</dd><dt>Employees</dt><dd class="mono">${o.estimated_num_employees ? fmt(o.estimated_num_employees) : "—"}</dd><dt>Headquarters</dt><dd>${esc(loc(o) || "—")}</dd></dl></section>` : ""}
    <section class="dr-sec"><h3>Where this record comes from</h3><dl class="kv"><dt>Source</dt><dd>${p.source_url ? `<a href="${esc(p.source_url)}" target="_blank" rel="noopener">${esc(SRC[p.source] || p.source)} ${icon("ext")}</a>` : esc(SRC[p.source] || p.source)}</dd><dt>Email status</dt><dd><span class="status"><span class="dot st-${esc((r || p).email_status)}"></span>${esc(STATUS[(r || p).email_status] || "—")}</span></dd></dl></section>
  </div>`);
  const d = $("#drawer");
  $("[data-close]", d).onclick = closeDrawer;
  $$("[data-dr]", d).forEach((b) => b.onclick = async () => {
    const a = b.dataset.dr;
    if (a === "reveal") { await revealPerson(id); b.remove(); }
    if (a === "phone") { const x = await revealPerson(id, true); b.outerHTML = x?.phone_numbers?.length ? `<span class="mono">${esc(x.phone_numbers[0].raw_number)}</span>` : '<span class="faint">Not found</span>'; }
    if (a === "save") { await post("/contacts", { person_id: id }); toast("Saved to Contacts"); }
    if (a === "list") { const l = await chooseList("people"); if (l) { await post(`/lists/${l}/items`, { person_ids: [id] }); toast("Added to list"); } }
    if (a === "seq") { const s = await chooseSequence(); if (s) { const [cid] = await savePeopleAsContacts([id]); await post(`/sequences/${s.id}/enroll`, { contact_ids: [cid] }); toast(`Added to ${s.name}`); } }
  });
}
async function companyDrawer(id) {
  openDrawer(`<div class="dr-body"><div class="skel" style="margin-top:24px;width:60%"></div></div>`);
  const [{ organization: o }, ppl] = await Promise.all([api(`/organizations/${id}`), api(`/organizations/${id}/people?per_page=25`)]);
  const ids = [o.ticker && `Ticker ${o.ticker}${o.exchange ? " · " + o.exchange : ""}`, o.cik && `SEC CIK ${o.cik}`, o.lei && `LEI ${o.lei}`, o.company_number && `Reg. no. ${o.company_number}`].filter(Boolean);
  openDrawer(`<div class="dr-head">${logo(o.name, true)}<div><h2>${esc(o.name)}</h2><p>${o.domain ? `<a href="https://${esc(o.domain)}" target="_blank" rel="noopener">${esc(o.domain)}</a>` : "No website on file"}${o.linkedin_url ? " " + liLink(o.linkedin_url) : ""}</p><p class="faint" style="font-size:12px">${esc(o.industry || "")}</p></div><button class="btn icon ghost dr-close" data-close aria-label="Close">${icon("x")}</button></div>
  <div class="dr-actions"><button class="btn primary" data-dr="people">${icon("people")} Find people here</button><button class="btn" data-dr="list">${icon("list")} Add to list</button></div>
  <div class="dr-body">
    <section class="dr-sec"><h3>Overview</h3><dl class="kv"><dt>Industry</dt><dd>${esc(o.industry || "—")}${o.sic_code ? ` <span class="tag">SIC ${esc(o.sic_code)}</span>` : ""}</dd><dt>Employees</dt><dd class="mono">${o.estimated_num_employees ? fmt(o.estimated_num_employees) : "—"}</dd><dt>Founded</dt><dd class="mono">${o.founded_year || "—"}</dd><dt>Headquarters</dt><dd>${esc([o.address, loc(o), o.postal_code].filter(Boolean).join(", ") || "—")}</dd><dt>Phone</dt><dd class="mono">${esc(o.phone || "—")}</dd><dt>Status</dt><dd>${esc(o.status || "—")}</dd></dl></section>
    <section class="dr-sec"><h3>Email format</h3><dl class="kv"><dt>Pattern</dt><dd class="mono">${esc(o.email_pattern || "Not learned yet")}</dd><dt>Mail server</dt><dd>${o.mx_valid === false ? '<span class="status"><span class="dot st-invalid"></span>No MX record</span>' : o.mx_valid ? '<span class="status"><span class="dot st-verified"></span>Accepts mail</span>' : '<span class="faint">Not checked</span>'}</dd></dl></section>
    ${ids.length ? `<section class="dr-sec"><h3>Identifiers</h3><div style="display:flex;gap:6px;flex-wrap:wrap">${ids.map((x) => `<span class="tag mono">${esc(x)}</span>`).join("")}</div></section>` : ""}
    <section class="dr-sec"><h3>People · <span class="mono">${fmt(ppl.pagination.total_entries)}</span></h3>${ppl.people.length ? ppl.people.map((p) => `<div class="who" style="padding:8px 0;border-bottom:1px solid var(--line-2)">${avatar(p.name)}<div class="t" style="flex:1"><button class="nm" data-open-person="${p.id}">${esc(p.name)}</button><div class="meta">${esc(p.title || "")}</div></div><div>${emailCell(p)}</div></div>`).join("") : '<p class="muted">No people on file yet. Use Enrich to find someone here by name.</p>'}</section>
    <section class="dr-sec"><h3>Where this record comes from</h3><p>${o.source_url ? `<a href="${esc(o.source_url)}" target="_blank" rel="noopener">${esc(SRC[o.source] || o.source)} ${icon("ext")}</a>` : esc(SRC[o.source] || o.source)}</p></section>
  </div>`);
  const d = $("#drawer");
  $("[data-close]", d).onclick = closeDrawer;
  $('[data-dr="people"]', d).onclick = () => { state.p = { filters: o.domain ? { q_organization_domains_list: [o.domain] } : { q_organization_name: o.name }, page: 1, tab: "all" }; closeDrawer(); location.hash = "#/people"; route(); };
  $('[data-dr="list"]', d).onclick = async () => { const l = await chooseList("companies"); if (l) { await post(`/lists/${l}/items`, { organization_ids: [o.id] }); toast("Added to list"); } };
}

/* ---------- filter panel ---------- */
function renderFilters(el, sections, vals, apply) {
  el.innerHTML = `<div class="filters-head">Filters <button type="button" data-reset>Clear all</button></div><div class="filters-body">${sections.map((s) => {
    const v = vals[s.key]; const n = Array.isArray(v) ? v.length : v ? 1 : 0;
    const body = s.type === "checks"
      ? `<div class="opts">${s.options.map((o) => `<label><input type="checkbox" data-k="${s.key}" value="${esc(o[0])}" ${(v || []).includes(o[0]) ? "checked" : ""}> ${esc(o[1])}</label>`).join("")}</div>`
      : `<input data-k="${s.key}" value="${esc(Array.isArray(v) ? v.join(", ") : v || "")}" placeholder="${esc(s.ph || "")}" aria-label="${esc(s.label)}">${s.hint ? `<div class="hint">${esc(s.hint)}</div>` : ""}`;
    return `<details class="fsec" ${n || s.open ? "open" : ""}><summary>${icon(s.icon)}${esc(s.label)}${n ? `<span class="cnt">${n}</span>` : ""}${icon("chev", "chev")}</summary><div class="fbody">${body}</div></details>`;
  }).join("")}</div><div class="filters-foot"><button class="btn primary" data-apply>Apply filters</button><button class="btn ftoggle" data-closef>Done</button></div>`;
  const read = () => {
    const o = {};
    sections.forEach((s) => {
      if (s.type === "checks") o[s.key] = $$(`input[data-k="${s.key}"]:checked`, el).map((i) => i.value);
      else { const raw = $(`input[data-k="${s.key}"]`, el).value.trim(); o[s.key] = s.type === "list" ? raw.split(",").map((x) => x.trim()).filter(Boolean) : raw; }
    });
    return o;
  };
  $("[data-apply]", el).onclick = () => apply(read());
  $("[data-reset]", el).onclick = () => apply({});
  $("[data-closef]", el).onclick = () => el.classList.remove("open");
  el.onkeydown = (e) => { if (e.key === "Enter" && e.target.matches("input:not([type=checkbox])")) { e.preventDefault(); apply(read()); } };
  $$("input[type=checkbox]", el).forEach((c) => (c.onchange = () => apply(read())));
}
function chipRow(sections, vals, onRemove) {
  const chips = [];
  for (const s of sections) {
    const v = vals[s.key];
    if (!v || (Array.isArray(v) && !v.length)) continue;
    (Array.isArray(v) ? v : [v]).forEach((x) => chips.push(`<span class="chip"><b>${esc(s.label)}:</b> ${esc(s.options ? lbl(s.options, x) : x)} <button data-unchip="${esc(s.key)}" data-val="${esc(x)}" aria-label="Remove ${esc(s.label)} ${esc(x)}">×</button></span>`));
  }
  setTimeout(() => $$("[data-unchip]").forEach((b) => (b.onclick = () => {
    const k = b.dataset.unchip; const v = vals[k];
    const next = { ...vals, [k]: Array.isArray(v) ? v.filter((x) => x !== b.dataset.val) : "" };
    onRemove(next);
  })));
  return chips.length ? `<div class="chiprow">${chips.join("")}</div>` : "";
}
function pager(pg) {
  if (!pg.total_entries) return "";
  const from = (pg.page - 1) * pg.per_page + 1, to = Math.min(pg.page * pg.per_page, pg.total_entries);
  return `<div class="pager"><span><span class="mono">${fmt(from)}–${fmt(to)}</span> of <span class="mono">${fmt(pg.total_entries)}</span></span><span style="display:flex;gap:6px"><button class="btn sm" data-page="${pg.page - 1}" ${pg.page <= 1 ? "disabled" : ""}>${icon("back")} Previous</button><button class="btn sm" data-page="${pg.page + 1}" ${pg.page >= pg.total_pages ? "disabled" : ""}>Next</button></span></div>`;
}
const loadingRows = (cols, n = 8) => Array.from({ length: n }, () => `<tr>${Array.from({ length: cols }, (_, i) => `<td><div class="skel" style="width:${i === 0 ? 16 : 40 + ((i * 37) % 50)}%"></div></td>`).join("")}</tr>`).join("");

/* ---------- People ---------- */
const PEOPLE_FILTERS = [
  { key: "q_person_name", label: "Name", icon: "user", type: "text", ph: "e.g. Priya Nair" },
  { key: "person_titles", label: "Job titles", icon: "brief", type: "list", ph: "CEO, VP Sales", hint: "Comma-separated. Matches anywhere in the title.", open: true },
  { key: "person_not_titles", label: "Exclude titles", icon: "minus", type: "list", ph: "Assistant, Intern" },
  { key: "person_seniorities", label: "Seniority", icon: "layers", type: "checks", options: SENIORITIES },
  { key: "person_departments", label: "Department", icon: "grid", type: "checks", options: DEPARTMENTS },
  { key: "person_locations", label: "Location", icon: "pin", type: "list", ph: "India, London, CA", hint: "City, state or country code. Matches the person or their company." },
  { key: "q_organization_name", label: "Company", icon: "building", type: "text", ph: "e.g. Udacity" },
  { key: "q_organization_domains_list", label: "Company domains", icon: "globe", type: "list", ph: "stripe.com, tcs.com" },
  { key: "organization_industries", label: "Industry", icon: "factory", type: "list", ph: "software, banking" },
  { key: "organization_num_employees_ranges", label: "Employees", icon: "people", type: "checks", options: EMP },
  { key: "contact_email_status", label: "Email status", icon: "mail", type: "checks", options: EMAIL_ST },
  { key: "q_keywords", label: "Keywords", icon: "tag", type: "text", ph: "Matches name, title, company or industry" },
  { key: "person_sources", label: "Data source", icon: "db", type: "checks", options: PERSON_SOURCES },
];
const PEOPLE_TABS = { all: ["All people", {}], verified: ["Verified email", { contact_email_status: ["verified"] }], execs: ["Executives", { person_seniorities: ["owner", "founder", "c_suite", "vp"] }] };

views.people = async () => {
  const st = state.p;
  $("#view").innerHTML = `<div class="ph"><div><h1>People</h1><p>Search is free. Accessing an email uses 1 credit.</p></div><div class="ph-actions"><button class="btn ftoggle" id="fopen">${icon("filter")} Filters</button><button class="btn" id="exp">${icon("download")} Export</button></div></div>
  <div class="tabs" role="tablist">${Object.entries(PEOPLE_TABS).map(([k, [t]]) => `<button class="tab ${st.tab === k ? "on" : ""}" role="tab" aria-selected="${st.tab === k}" data-tab="${k}">${t}</button>`).join("")}</div>
  <div class="work"><aside class="filters" id="pf" aria-label="People filters"></aside><section class="results" id="pres"></section></div>`;
  const apply = (f) => { st.filters = f; st.page = 1; views.people(); };
  renderFilters($("#pf"), PEOPLE_FILTERS, st.filters, apply);
  $("#fopen").onclick = () => $("#pf").classList.add("open");
  $$("[data-tab]").forEach((b) => (b.onclick = () => { st.tab = b.dataset.tab; st.page = 1; views.people(); }));
  $("#exp").onclick = exportPeople;
  setBulk("people", () => `<button class="btn credit" data-bulk="reveal">${icon("mail")} Access emails</button><button class="btn" data-bulk="save">${icon("contact")} Save</button><button class="btn" data-bulk="list">${icon("list")} Add to list</button><button class="btn" data-bulk="sequence">${icon("send")} Add to sequence</button>`);
  const res = $("#pres");
  res.innerHTML = `${chipRow(PEOPLE_FILTERS, st.filters, apply)}<div class="tablewrap"><table class="dt"><tbody>${loadingRows(6)}</tbody></table></div>`;
  const q = { ...st.filters, ...PEOPLE_TABS[st.tab][1], page: st.page, per_page: 25 };
  const r = await api(`/mixed_people/api_search?${qs(q)}`);
  if (!r.people.length) {
    res.innerHTML = `${chipRow(PEOPLE_FILTERS, st.filters, apply)}<div class="tablewrap"><div class="empty"><h3>No people match these filters</h3><p>Remove a filter, or grow the library from Data.</p><button class="btn" id="clr">Clear filters</button></div></div>`;
    $("#clr").onclick = () => apply({});
    return;
  }
  res.innerHTML = `${chipRow(PEOPLE_FILTERS, st.filters, apply)}<div class="rbar"><span class="count"><span>${fmt(r.pagination.total_entries)}</span> people</span><span class="muted" style="font-size:12px">Sorted by date added</span></div>
  <div class="tablewrap"><table class="dt"><thead><tr><th class="cb"><input type="checkbox" data-selall aria-label="Select page"></th><th>Name</th><th>Title</th><th>Company</th><th>Email</th><th>Source</th></tr></thead><tbody>
  ${r.people.map((p) => { const o = p.organization; return `<tr data-id="${p.id}"><td class="cb"><input type="checkbox" data-sel="${p.id}" aria-label="Select ${esc(p.name)}"></td>
    <td><div class="who">${avatar(p.name)}<div class="t"><button class="nm" data-open-person="${p.id}">${esc(p.name)}</button><div class="meta">${liLink(p.linkedin_url)}${esc(loc(p) || loc(o))}</div></div></div></td>
    <td>${esc(p.title || "—")}${p.seniority ? `<div class="sub">${esc(lbl(SENIORITIES, p.seniority))}${p.department ? " · " + esc(lbl(DEPARTMENTS, p.department)) : ""}</div>` : ""}</td>
    <td>${o ? `<div class="co">${logo(o.name)}<div class="t"><button class="nm" data-open-company="${o.id}">${esc(o.name)}</button><div class="sub">${esc(o.domain || o.industry || "")}</div></div></div>` : esc(p.organization_name || "—")}</td>
    <td>${emailCell(p)}</td><td><span class="tag">${esc(SRC[p.source] || p.source)}</span></td></tr>`; }).join("")}
  </tbody></table>${pager(r.pagination)}</div>`;
  $$("[data-page]", res).forEach((b) => (b.onclick = () => { st.page = +b.dataset.page; views.people(); window.scrollTo(0, 0); }));
};
async function exportPeople() {
  const q = { ...state.p.filters, ...PEOPLE_TABS[state.p.tab][1] };
  const r = await dialog({ title: "Export people", body: "Exports up to 5,000 rows matching the current search.", ok: "Export CSV", fields: [{ name: "reveal", type: "checkbox", text: "Include emails (1 credit per row)" }] });
  if (!r) return;
  window.open(`${API}/people/export.csv?${qs({ ...q, limit: 5000, reveal: r.reveal })}`);
}

/* ---------- Companies ---------- */
const COMPANY_FILTERS = [
  { key: "q_organization_name", label: "Company name", icon: "building", type: "text", ph: "e.g. Target", open: true },
  { key: "q_organization_domains_list", label: "Domains", icon: "globe", type: "list", ph: "stripe.com" },
  { key: "organization_locations", label: "Location", icon: "pin", type: "list", ph: "IN, Mumbai, London" },
  { key: "organization_industries", label: "Industry", icon: "factory", type: "list", ph: "software, retail" },
  { key: "organization_sic_codes", label: "SIC code", icon: "tag", type: "list", ph: "73, 6022", hint: "Prefix match, e.g. 73 = business services." },
  { key: "organization_num_employees_ranges", label: "Employees", icon: "people", type: "checks", options: EMP },
  { key: "q_organization_keyword_tags", label: "Keywords", icon: "search", type: "list", ph: "fintech, payments" },
  { key: "organization_sources", label: "Data source", icon: "db", type: "checks", options: ORG_SOURCES },
];
const COMPANY_TABS = { all: ["All companies", {}], web: ["Has website", { has_domain: "true" }] };
views.companies = async () => {
  const st = state.c;
  $("#view").innerHTML = `<div class="ph"><div><h1>Companies</h1><p>Registered companies with firmographics, email format and the people on file.</p></div><div class="ph-actions"><button class="btn ftoggle" id="fopen">${icon("filter")} Filters</button></div></div>
  <div class="tabs" role="tablist">${Object.entries(COMPANY_TABS).map(([k, [t]]) => `<button class="tab ${st.tab === k ? "on" : ""}" role="tab" data-tab="${k}">${t}</button>`).join("")}</div>
  <div class="work"><aside class="filters" id="cf" aria-label="Company filters"></aside><section class="results" id="cres"></section></div>`;
  const apply = (f) => { st.filters = f; st.page = 1; views.companies(); };
  renderFilters($("#cf"), COMPANY_FILTERS, st.filters, apply);
  $("#fopen").onclick = () => $("#cf").classList.add("open");
  $$("[data-tab]").forEach((b) => (b.onclick = () => { st.tab = b.dataset.tab; st.page = 1; views.companies(); }));
  setBulk("companies", () => `<button class="btn" data-bulk="list">${icon("list")} Add to list</button>`);
  const res = $("#cres");
  res.innerHTML = `${chipRow(COMPANY_FILTERS, st.filters, apply)}<div class="tablewrap"><table class="dt"><tbody>${loadingRows(6)}</tbody></table></div>`;
  const r = await api(`/mixed_companies/search?${qs({ ...st.filters, ...COMPANY_TABS[st.tab][1], page: st.page, per_page: 25 })}`);
  if (!r.organizations.length) { res.innerHTML = `${chipRow(COMPANY_FILTERS, st.filters, apply)}<div class="tablewrap"><div class="empty"><h3>No companies match these filters</h3><p>Remove a filter, or load more registries from Data.</p></div></div>`; return; }
  res.innerHTML = `${chipRow(COMPANY_FILTERS, st.filters, apply)}<div class="rbar"><span class="count"><span>${fmt(r.pagination.total_entries)}</span> companies</span><span class="muted" style="font-size:12px">Largest first</span></div>
  <div class="tablewrap"><table class="dt"><thead><tr><th class="cb"><input type="checkbox" data-selall aria-label="Select page"></th><th>Company</th><th>Industry</th><th>Employees</th><th>Location</th><th>People</th><th>Email format</th><th>Source</th></tr></thead><tbody>
  ${r.organizations.map((o) => `<tr data-id="${o.id}"><td class="cb"><input type="checkbox" data-sel="${o.id}" aria-label="Select ${esc(o.name)}"></td>
    <td><div class="co">${logo(o.name)}<div class="t"><button class="nm" data-open-company="${o.id}">${esc(o.name)}</button><div class="sub">${o.domain ? esc(o.domain) : ""}${o.ticker ? ` <span class="tag mono">${esc(o.ticker)}</span>` : ""}</div></div></div></td>
    <td>${esc(o.industry || "—")}</td><td class="mono">${o.estimated_num_employees ? fmt(o.estimated_num_employees) : "—"}</td><td>${esc(loc(o) || "—")}</td>
    <td class="mono">${o.num_people ? `<button class="btn sm ghost" data-ppl="${o.id}" data-name="${esc(o.name)}" data-dom="${esc(o.domain || "")}">${fmt(o.num_people)}</button>` : '<span class="faint">0</span>'}</td>
    <td class="mono">${esc(o.email_pattern || "—")}</td><td><span class="tag">${esc(SRC[o.source] || o.source)}</span></td></tr>`).join("")}
  </tbody></table>${pager(r.pagination)}</div>`;
  $$("[data-page]", res).forEach((b) => (b.onclick = () => { st.page = +b.dataset.page; views.companies(); window.scrollTo(0, 0); }));
  $$("[data-ppl]", res).forEach((b) => (b.onclick = () => { state.p = { filters: b.dataset.dom ? { q_organization_domains_list: [b.dataset.dom] } : { q_organization_name: b.dataset.name }, page: 1, tab: "all" }; location.hash = "#/people"; }));
};

/* ---------- Contacts ---------- */
const STAGES = ["new", "contacted", "replied", "meeting", "customer", "lost"];
views.contacts = async () => {
  const stage = (location.hash.match(/stage=(\w+)/) || [])[1] || "";
  const q = (location.hash.match(/q=([^&]+)/) || [])[1] || "";
  const r = await api(`/contacts?per_page=100&q=${q}`);
  const rows = r.contacts.filter((c) => !stage || c.stage === stage);
  const counts = STAGES.reduce((m, s) => ((m[s] = r.contacts.filter((c) => c.stage === s).length), m), {});
  $("#view").innerHTML = `<div class="ph"><div><h1>Contacts</h1><p>People you saved or accessed. Stages update automatically when someone replies.</p></div><div class="ph-actions"><button class="btn" id="add">${icon("plus")} Add contact</button><a class="btn" href="${API}/contacts/export.csv">${icon("download")} Export</a></div></div>
  <div class="tabs"><a class="tab ${!stage ? "on" : ""}" href="#/contacts">All <span class="n">${r.pagination.total_entries}</span></a>${STAGES.map((s) => `<a class="tab ${stage === s ? "on" : ""}" href="#/contacts?stage=${s}">${s[0].toUpperCase() + s.slice(1)} <span class="n">${counts[s]}</span></a>`).join("")}</div>
  <div class="tablewrap">${rows.length ? `<table class="dt"><thead><tr><th class="cb"><input type="checkbox" data-selall aria-label="Select all"></th><th>Name</th><th>Company</th><th>Email</th><th>Phone</th><th>Stage</th><th>Added</th></tr></thead><tbody>
  ${rows.map((c) => `<tr data-id="${c.id}"><td class="cb"><input type="checkbox" data-sel="${c.id}" aria-label="Select ${esc(c.name)}"></td>
    <td><div class="who">${avatar(c.name)}<div class="t">${c.person_id ? `<button class="nm" data-open-person="${c.person_id}">${esc(c.name)}</button>` : `<b>${esc(c.name)}</b>`}<div class="meta">${liLink(c.linkedin_url)}${esc(c.title || "")}</div></div></div></td>
    <td>${c.organization_name ? `<div class="co">${logo(c.organization_name)}<span>${esc(c.organization_name)}</span></div>` : "—"}</td>
    <td>${c.email ? emailHTML({ email: c.email, email_status: c.email_status }) : `<span class="nomail">${c.email_status === "suppressed" ? "Opted out" : "No email"}</span>`}</td>
    <td class="mono">${esc(c.phone || "—")}</td>
    <td><select class="select-inline" data-stage="${c.id}" aria-label="Stage">${STAGES.map((s) => `<option ${s === c.stage ? "selected" : ""}>${s}</option>`).join("")}</select></td>
    <td class="mono faint">${day(c.created_at)}</td></tr>`).join("")}</tbody></table>`
    : `<div class="empty"><h3>${stage ? `No contacts in ${stage}` : "No contacts yet"}</h3><p>Access an email in People and the person lands here.</p><a class="btn primary" href="#/people">${icon("search")} Find people</a></div>`}</div>`;
  setBulk("contacts", () => `<button class="btn" data-bulk="sequence">${icon("send")} Add to sequence</button><button class="btn" data-bulk="delete">${icon("trash")} Remove</button>`);
  $$("[data-stage]").forEach((s) => (s.onchange = () => api(`/contacts/${s.dataset.stage}`, { method: "PATCH", body: JSON.stringify({ stage: s.value }) }).then(() => toast(`Moved to ${s.value}`))));
  $("#add").onclick = async () => {
    const f = await dialog({ title: "Add contact", ok: "Add contact", fields: [{ name: "name", label: "Full name", required: true }, { name: "email", label: "Work email", type: "email" }, { name: "title", label: "Title" }, { name: "organization_name", label: "Company" }] });
    if (!f) return;
    const [first_name, ...rest] = f.name.split(" ");
    await post("/contacts", { first_name, last_name: rest.join(" "), email: f.email || null, title: f.title || null, organization_name: f.organization_name || null });
    toast("Contact added"); views.contacts();
  };
};

/* ---------- Lists ---------- */
views.lists = async () => {
  const idm = location.hash.match(/id=(\d+)/);
  if (idm) return listDetail(+idm[1]);
  const { lists } = await api("/lists");
  $("#view").innerHTML = `<div class="ph"><div><h1>Lists</h1><p>Group people or companies for export and outreach.</p></div><div class="ph-actions"><button class="btn primary" id="new">${icon("plus")} New list</button></div></div>
  <div class="tablewrap">${lists.length ? `<table class="dt"><thead><tr><th>Name</th><th>Type</th><th>Records</th><th>Created</th><th></th></tr></thead><tbody>${lists.map((l) => `<tr><td><a class="who" href="#/lists?id=${l.id}"><span class="logo" style="background:var(--line-2);color:var(--ink)">${icon(l.kind === "people" ? "people" : "building")}</span><b style="color:var(--text)">${esc(l.name)}</b></a></td><td>${l.kind === "people" ? "People" : "Companies"}</td><td class="mono">${fmt(l.count)}</td><td class="mono faint">${day(l.created_at)}</td><td style="text-align:right"><button class="btn sm ghost icon" data-del="${l.id}" aria-label="Delete ${esc(l.name)}">${icon("trash")}</button></td></tr>`).join("")}</tbody></table>`
    : `<div class="empty"><h3>No lists yet</h3><p>Select rows in People or Companies and choose Add to list.</p><button class="btn primary" id="new2">${icon("plus")} New list</button></div>`}</div>`;
  const make = async () => { const f = await dialog({ title: "New list", ok: "Create list", fields: [{ name: "name", label: "Name", required: true }, { name: "kind", label: "Contains", type: "select", options: [["people", "People"], ["companies", "Companies"]], value: "people" }] }); if (f) { const r = await post("/lists", f); location.hash = `#/lists?id=${r.list.id}`; } };
  $("#new").onclick = make; $("#new2") && ($("#new2").onclick = make);
  $$("[data-del]").forEach((b) => (b.onclick = async () => { if (await confirmDlg("Delete list", "The people and companies stay in the library.", "Delete list", true)) { await del(`/lists/${b.dataset.del}`); views.lists(); } }));
};
async function listDetail(id) {
  const r = await api(`/lists/${id}/items?per_page=100`);
  $("#view").innerHTML = `<a class="back" href="#/lists">${icon("back")} Lists</a><div class="ph"><div><h1>${esc(r.list.name)}</h1><p><span class="mono">${fmt(r.pagination.total_entries)}</span> ${r.list.kind}</p></div><div class="ph-actions"><a class="btn" href="${API}/lists/${id}/export.csv">${icon("download")} Export</a>${r.list.kind === "people" ? `<button class="btn credit" id="expE">${icon("mail")} Export with emails</button>` : ""}</div></div>
  <div class="tablewrap">${r.people.length ? `<table class="dt"><thead><tr><th class="cb"><input type="checkbox" data-selall aria-label="Select all"></th><th>Name</th><th>Title</th><th>Company</th><th>Email</th></tr></thead><tbody>${r.people.map((p) => `<tr data-id="${p.id}"><td class="cb"><input type="checkbox" data-sel="${p.id}"></td><td><div class="who">${avatar(p.name)}<button class="nm" data-open-person="${p.id}">${esc(p.name)}</button></div></td><td>${esc(p.title || "—")}</td><td>${p.organization ? `<div class="co">${logo(p.organization.name)}<button class="nm" data-open-company="${p.organization.id}">${esc(p.organization.name)}</button></div>` : "—"}</td><td>${emailCell(p)}</td></tr>`).join("")}</tbody></table>` : ""}
  ${r.organizations.length ? `<table class="dt"><thead><tr><th>Company</th><th>Industry</th><th>Location</th></tr></thead><tbody>${r.organizations.map((o) => `<tr><td><div class="co">${logo(o.name)}<button class="nm" data-open-company="${o.id}">${esc(o.name)}</button></div></td><td>${esc(o.industry || "—")}</td><td>${esc(loc(o) || "—")}</td></tr>`).join("")}</tbody></table>` : ""}
  ${!r.people.length && !r.organizations.length ? `<div class="empty"><h3>This list is empty</h3><p>Select rows in People or Companies and choose Add to list.</p></div>` : ""}</div>`;
  setBulk("people", () => `<button class="btn credit" data-bulk="reveal">${icon("mail")} Access emails</button><button class="btn" data-bulk="sequence">${icon("send")} Add to sequence</button>`);
  $("#expE") && ($("#expE").onclick = async () => { if (await confirmDlg("Export with emails", `Uses up to ${r.people.length} credits, one per row.`, "Export CSV")) window.open(`${API}/lists/${id}/export.csv?reveal=true`); });
}

/* ---------- Sequences ---------- */
views.sequences = async () => {
  const idm = location.hash.match(/id=(\d+)/);
  if (idm) return sequenceDetail(+idm[1]);
  const { sequences } = await api("/sequences");
  $("#view").innerHTML = `<div class="ph"><div><h1>Sequences</h1><p>Multi-step email and task cadences. Replies and bounces stop a contact automatically.</p></div><div class="ph-actions"><button class="btn primary" id="new">${icon("plus")} New sequence</button></div></div>
  <div class="tablewrap">${sequences.length ? `<table class="dt"><thead><tr><th>Sequence</th><th>Steps</th><th>Active</th><th>Sent</th><th>Opened</th><th>Replied</th><th>Bounced</th><th></th></tr></thead><tbody>${sequences.map((s) => { const x = s.stats; const pct = (n) => (x.sent ? Math.round((n / x.sent) * 100) + "%" : "—"); return `<tr><td><a href="#/sequences?id=${s.id}"><b style="color:var(--text)">${esc(s.name)}</b></a><div class="sub">${fmt(x.enrolled)} enrolled</div></td><td class="mono">${s.steps.length}</td><td class="mono">${fmt(x.active)}</td><td class="mono">${fmt(x.sent)}</td><td class="mono">${fmt(x.opened)} <span class="faint">${pct(x.opened)}</span></td><td class="mono">${fmt(x.replied)} <span class="faint">${pct(x.replied)}</span></td><td class="mono">${fmt(x.bounced)}</td><td style="text-align:right"><button class="btn sm ghost icon" data-del="${s.id}" aria-label="Delete ${esc(s.name)}">${icon("trash")}</button></td></tr>`; }).join("")}</tbody></table>`
    : `<div class="empty"><h3>No sequences yet</h3><p>Create one, add steps, then enroll contacts from People or Contacts.</p><button class="btn primary" id="new2">${icon("plus")} New sequence</button></div>`}</div>`;
  const make = async () => { const f = await dialog({ title: "New sequence", ok: "Create sequence", fields: [{ name: "name", label: "Name", required: true, placeholder: "e.g. Founder intro" }] }); if (f) { const r = await post("/sequences", f); location.hash = `#/sequences?id=${r.sequence.id}`; } };
  $("#new").onclick = make; $("#new2") && ($("#new2").onclick = make);
  $$("[data-del]").forEach((b) => (b.onclick = async () => { if (await confirmDlg("Delete sequence", "Enrolled contacts stop receiving its steps.", "Delete sequence", true)) { await del(`/sequences/${b.dataset.del}`); views.sequences(); } }));
};
async function sequenceDetail(id) {
  const [{ sequence: s }, { events }] = await Promise.all([api(`/sequences/${id}`), api(`/sequences/${id}/events`)]);
  const x = s.stats;
  const kindIcon = { email: "mail", call: "phone", linkedin: "user", task: "check" };
  $("#view").innerHTML = `<a class="back" href="#/sequences">${icon("back")} Sequences</a><div class="ph"><div><h1>${esc(s.name)}</h1><p>${s.steps.length} step${s.steps.length === 1 ? "" : "s"} · ${fmt(x.enrolled)} enrolled</p></div><div class="ph-actions"><a class="btn" href="#/contacts">${icon("plus")} Add contacts</a><button class="btn primary" id="run">${icon("play")} Send due steps now</button></div></div>
  <div class="stats">${[["Active", x.active], ["Sent", x.sent], ["Opened", x.opened], ["Replied", x.replied], ["Bounced", x.bounced], ["Finished", x.finished]].map(([k, v]) => `<div><b>${fmt(v)}</b><span>${k}</span></div>`).join("")}</div>
  <div class="grid2"><div><div class="card"><h2>Steps</h2>${s.steps.map((t) => `<div class="steprow"><span class="stepnum">${t.position}</span><div><div class="wait">${icon(kindIcon[t.kind] || "mail")} ${t.kind[0].toUpperCase() + t.kind.slice(1)} · ${t.position === 1 ? (t.delay_days ? `day ${t.delay_days}` : "immediately") : `${t.delay_days} day${t.delay_days === 1 ? "" : "s"} after step ${t.position - 1}`}</div><div class="subj">${esc(t.subject || "(no subject)")}</div><div class="body">${esc(t.body)}</div></div><button class="btn sm ghost icon" data-delstep="${t.id}" aria-label="Delete step ${t.position}">${icon("trash")}</button></div>`).join("") || '<p class="muted">No steps yet. Add the first one below.</p>'}</div>
  <div class="card"><h2>Add a step</h2><div class="grid2" style="gap:10px"><label class="fld"><span>Type</span><select id="sk"><option value="email">Email</option><option value="call">Call task</option><option value="linkedin">LinkedIn task</option><option value="task">Other task</option></select></label><label class="fld"><span>Wait (days after previous)</span><input id="sd" type="number" min="0" value="${s.steps.length ? 3 : 0}"></label></div><label class="fld"><span>Subject</span><input id="ss" placeholder="Quick question, {{first_name}}"></label><label class="fld"><span>Body</span><textarea id="sb" placeholder="Hi {{first_name}},&#10;&#10;I noticed {{company}} …"></textarea></label><p class="muted" style="font-size:12px;margin:-4px 0 12px">Variables: {{first_name}} {{last_name}} {{title}} {{company}}. Every email gets an unsubscribe link and open tracking.</p><button class="btn primary" id="add">${icon("plus")} Add step</button></div></div>
  <div class="card"><h2>Activity</h2>${events.length ? `<ul class="feed">${events.map((e) => `<li><span class="sig ${e.kind === "sent" ? "reply" : e.kind === "opened" ? "open" : e.kind === "replied" ? "new_contact" : e.kind === "failed" || e.kind === "bounced" ? "bounce" : "auto_reply"}">${esc(e.kind)}</span><span>Contact #${e.contact_id}<div class="faint" style="font-size:12px">${esc(e.detail || "")}</div></span><span class="when">${when(e.at)}</span></li>`).join("")}</ul>` : '<p class="muted">Nothing sent yet. Enroll contacts, then send due steps. Without SMTP settings in .env, sends are logged as dry runs.</p>'}</div></div>`;
  $("#add").onclick = async () => { await post(`/sequences/${id}/steps`, { kind: $("#sk").value, delay_days: +$("#sd").value, subject: $("#ss").value, body: $("#sb").value }); toast("Step added"); sequenceDetail(id); };
  $("#run").onclick = async () => { const r = await post(`/sequences/${id}/run`); toast(`Sent ${r.sent} · failed ${r.failed} · skipped ${r.skipped}`); sequenceDetail(id); };
  $$("[data-delstep]").forEach((b) => (b.onclick = async () => { await del(`/sequences/${id}/steps/${b.dataset.delstep}`); sequenceDetail(id); }));
}

/* ---------- Enrich ---------- */
views.enrich = () => {
  $("#view").innerHTML = `<div class="ph"><div><h1>Enrich</h1><p>Find a work email from a name and company, or look up a company's email format.</p></div></div>
  <div class="grid2"><div><div class="card"><h2>Find an email</h2><form id="ef"><div class="grid2" style="gap:10px"><label class="fld"><span>First name</span><input name="first_name" required></label><label class="fld"><span>Last name</span><input name="last_name"></label></div><label class="fld"><span>Company domain</span><input name="domain" placeholder="acme.com"></label><label class="fld"><span>Or company name</span><input name="organization_name"></label><label class="fld"><span>Or LinkedIn URL</span><input name="linkedin_url" placeholder="linkedin.com/in/…"></label><label class="check" style="margin-bottom:12px"><input type="checkbox" name="reveal_phone_number"> Also find a phone number (8 credits)</label><div><button class="btn credit">${icon("search")} Find email · 1 credit</button></div></form><div id="eo" style="margin-top:14px"></div></div>
  <div class="card"><h2>Company lookup</h2><form id="cfm" style="display:flex;gap:8px"><input name="domain" placeholder="stripe.com" required aria-label="Domain"><button class="btn">Look up</button></form><div id="co" style="margin-top:12px"></div></div></div>
  <div class="card"><h2>Bulk find <span class="faint" style="font-weight:400;font-size:12px">up to 10 per run</span></h2><label class="fld"><span>One person per line: first, last, domain</span><textarea id="bulk" placeholder="Priya, Nair, acme.com&#10;Arjun, Mehta, globex.io"></textarea></label><button class="btn credit" id="bgo">${icon("search")} Find emails</button><div id="bo" style="margin-top:14px"></div></div></div>`;
  $("#ef").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target)); f.reveal_phone_number = !!f.reveal_phone_number;
    const r = await post(`/people/match?${qs(f)}`);
    const p = r.person;
    $("#eo").innerHTML = p ? `<div class="who" style="padding:12px;border:1px solid var(--line);border-radius:8px">${avatar(p.name)}<div class="t" style="flex:1"><b>${esc(p.name)}</b><div class="meta">${esc(p.title || p.organization?.name || "")} · match ${esc(r.match_confidence)}</div></div>${p.email ? emailHTML(p, true) : '<span class="nomail">No email found</span>'}</div>` : `<p class="muted">No match. Add a company domain so the email format can be applied.</p>`;
    refreshCredits();
  };
  $("#cfm").onsubmit = async (e) => {
    e.preventDefault();
    const r = await post(`/organizations/enrich?domain=${encodeURIComponent(e.target.domain.value)}`);
    const o = r.organization;
    $("#co").innerHTML = `<dl class="kv"><dt>Company</dt><dd>${o.id ? `<button class="nm" data-open-company="${o.id}" style="border:0;background:none;padding:0;color:var(--teal);cursor:pointer">${esc(o.name)}</button>` : '<span class="faint">Not in library</span>'}</dd><dt>Email format</dt><dd class="mono">${esc(o.email_pattern || "—")}${o.email_pattern_confidence ? ` <span class="faint">${Math.round(o.email_pattern_confidence * 100)}% confidence</span>` : ""}</dd><dt>Mail server</dt><dd>${o.mx_valid ? '<span class="status"><span class="dot st-verified"></span>Accepts mail</span>' : '<span class="status"><span class="dot st-invalid"></span>No MX record</span>'}</dd>${o.industry ? `<dt>Industry</dt><dd>${esc(o.industry)}</dd>` : ""}</dl>`;
  };
  $("#bgo").onclick = async () => {
    const details = $("#bulk").value.split("\n").map((l) => l.split(",").map((s) => s.trim())).filter((a) => a.length >= 3 && a[0]).slice(0, 10).map(([first_name, last_name, domain]) => ({ first_name, last_name, domain }));
    if (!details.length) return toast("Add at least one line: first, last, domain", true);
    const r = await post("/people/bulk_match", { details });
    $("#bo").innerHTML = `<div class="tablewrap"><table class="dt" style="min-width:0"><thead><tr><th>Name</th><th>Email</th></tr></thead><tbody>${r.matches.map((m, i) => `<tr><td>${esc(m ? m.name : `${details[i].first_name} ${details[i].last_name}`)}</td><td>${m?.email ? emailHTML(m, true) : '<span class="nomail">Not found</span>'}</td></tr>`).join("")}</tbody></table></div><p class="muted mono" style="font-size:12px">${r.credits_consumed} credits used</p>`;
    refreshCredits();
  };
};

/* ---------- Contribute ---------- */
views.contribute = async () => {
  const [st, { accounts }] = await Promise.all([api("/contribute/stats"), api("/mail_accounts")]);
  $("#view").innerHTML = `<div class="ph"><div><h1>Contribute</h1><p>Your mailbox and CRM are what make emails verified. This is how every large contact database is built.</p></div></div>
  <div class="card" style="margin-bottom:14px"><div class="consent"><label class="switch"><input type="checkbox" id="consent" ${st.contribute ? "checked" : ""} aria-label="Share my business contacts with the library"><i></i></label><div><b>Share my business contacts with the library</b><p class="muted" style="margin:4px 0 0">Names, titles, work emails and signature phones from mail you connect or upload. Personal addresses, newsletters and shared inboxes like info@ are skipped. Anyone can remove themselves at <a href="/api/v1/optout" target="_blank">the opt-out page</a>. Nothing is shared while this is off.</p></div></div></div>
  <div class="stats">${[["Contacts you added", st.my.people_added], ["Contacts you refreshed", st.my.people_updated], ["Messages scanned", st.my.messages], ["Library contributed people", st.network.contributed_people], ["Library verified emails", st.network.verified_emails], ["Opted out", st.network.suppressed]].map(([k, v]) => `<div><b>${fmt(v)}</b><span>${k}</span></div>`).join("")}</div>
  <div class="grid2"><div class="card"><h2>Connect a mailbox</h2><p class="muted" style="margin-top:-6px">For Gmail, turn on IMAP and create an app password. The worker syncs every 10 minutes.</p><form id="imap"><label class="fld"><span>Label</span><input name="label" placeholder="Work Gmail"></label><div class="grid2" style="grid-template-columns:3fr 1fr;gap:10px"><label class="fld"><span>IMAP server</span><input name="host" value="imap.gmail.com" required></label><label class="fld"><span>Port</span><input name="port" type="number" value="993"></label></div><label class="fld"><span>Email address</span><input name="username" type="email" required></label><label class="fld"><span>App password</span><input name="secret" type="password" required></label><div style="display:grid;gap:8px;margin-bottom:14px"><label class="check"><input type="checkbox" name="contribute" checked> Share contacts from this mailbox</label><label class="check"><input type="checkbox" name="is_sender"> Sequences send from this mailbox — watch it for replies and bounces</label></div><button class="btn primary">${icon("mail")} Connect mailbox</button></form>
    <h2 style="margin-top:22px">Connect HubSpot</h2><form id="hs" style="display:flex;gap:8px"><input name="secret" placeholder="Private app token (pat-…)" required aria-label="HubSpot token"><button class="btn">Connect</button></form><p class="faint" style="font-size:12px;margin:6px 0 0">Needs the crm.objects.contacts.read scope.</p></div>
  <div class="card"><h2>Upload an export</h2><label class="drop" id="drop"><input type="file" id="file" accept=".mbox,.eml,.csv,.txt">${icon("upload")}<div style="margin-top:6px"><b>Drop a file or click to choose</b></div><div style="font-size:12px;margin-top:4px">.mbox from Google Takeout, Apple Mail or Thunderbird · .eml · .csv from Google Contacts, Outlook, LinkedIn or a CRM</div></label><label class="check" style="margin:12px 0"><input type="checkbox" id="watch"> This export is from my sending mailbox — scan it for replies and bounces</label><div id="upOut" class="muted"></div>
    <h2 style="margin-top:22px">More sources</h2><pre class="code">python -m ingest.run webcrawl --from-db 500
python -m ingest.run verify_emails --limit 2000</pre></div></div>
  <div class="card"><h2>Connected accounts</h2>${accounts.length ? `<div class="tablewrap" style="border:0"><table class="dt" style="min-width:640px"><thead><tr><th>Account</th><th>Shares</th><th>Watches replies</th><th>Status</th><th>Messages</th><th>Last sync</th><th></th></tr></thead><tbody>${accounts.map((a) => `<tr><td><b>${esc(a.label)}</b><div class="sub">${esc(a.kind === "hubspot" ? "HubSpot" : a.username || "")}</div></td><td>${a.contribute ? "Yes" : "No"}</td><td>${a.is_sender ? "Yes" : "No"}</td><td><span class="status"><span class="dot st-${a.status === "ok" ? "verified" : a.status === "error" ? "invalid" : "guessed"}"></span>${a.status === "ok" ? "Syncing" : a.status === "error" ? "Error" : "Waiting"}</span>${a.error ? `<div class="sub" style="color:var(--red)">${esc(a.error).slice(0, 120)}</div>` : ""}</td><td class="mono">${fmt(a.messages_seen)}</td><td class="mono faint">${when(a.last_sync_at)}</td><td style="text-align:right;white-space:nowrap"><button class="btn sm" data-sync="${a.id}">Sync now</button> <button class="btn sm ghost icon" data-delacct="${a.id}" aria-label="Disconnect">${icon("trash")}</button></td></tr>`).join("")}</tbody></table></div>` : '<p class="muted">Nothing connected yet.</p>'}</div>
  ${st.recent.length ? `<div class="card"><h2>Recent contributions</h2><ul class="feed">${st.recent.map((r) => `<li><span class="tag">${esc(r.source)}</span><span><span class="mono">${fmt(r.people_added)}</span> added · <span class="mono">${fmt(r.people_updated)}</span> refreshed from <span class="mono">${fmt(r.messages)}</span> messages</span><span class="when">${when(r.at)}</span></li>`).join("")}</ul></div>` : ""}`;
  $("#consent").onchange = async (e) => { await post("/contribute/consent", { contribute: e.target.checked }); toast(e.target.checked ? "Sharing turned on" : "Sharing turned off"); };
  $("#imap").onsubmit = async (e) => { e.preventDefault(); const f = e.target; await post("/mail_accounts", { kind: "imap", label: f.label.value, host: f.host.value, port: +f.port.value, username: f.username.value, secret: f.secret.value, contribute: f.contribute.checked, is_sender: f.is_sender.checked }); toast("Mailbox connected"); views.contribute(); };
  $("#hs").onsubmit = async (e) => { e.preventDefault(); await post("/mail_accounts", { kind: "hubspot", label: "HubSpot", secret: e.target.secret.value, contribute: true }); toast("HubSpot connected"); views.contribute(); };
  $$("[data-sync]").forEach((b) => (b.onclick = async () => { b.disabled = true; b.textContent = "Syncing…"; const r = await post(`/mail_accounts/${b.dataset.sync}/sync`); toast(r.result.error ? `Sync failed: ${r.result.error}` : `Scanned ${r.result.messages} · added ${r.result.people_added}`, !!r.result.error); views.contribute(); }));
  $$("[data-delacct]").forEach((b) => (b.onclick = async () => { if (await confirmDlg("Disconnect account", "Contacts already contributed stay in the library.", "Disconnect", true)) { await del(`/mail_accounts/${b.dataset.delacct}`); views.contribute(); } }));
  const upload = async (file) => {
    const fd = new FormData(); fd.append("file", file); fd.append("watch", $("#watch").checked);
    $("#upOut").textContent = `Reading ${file.name}…`;
    try { const j = await post("/contribute/upload", fd); $("#upOut").innerHTML = `<b>${esc(file.name)}</b>: ${fmt(j.messages)} scanned · ${fmt(j.people_added)} added · ${fmt(j.people_updated)} refreshed · ${fmt(j.skipped)} skipped. ${esc(j.note || "")}`; } catch (e) { $("#upOut").textContent = e.message; }
  };
  $("#file").onchange = (e) => e.target.files[0] && upload(e.target.files[0]);
  const drop = $("#drop");
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]); };
};

/* ---------- Signals ---------- */
const SIG_LABEL = { reply: "Replied", bounce: "Bounced", job_change: "Job change", auto_reply: "Auto-reply", open: "Opened", new_contact: "New contact" };
views.signals = async () => {
  const kind = (location.hash.match(/kind=(\w+)/) || [])[1] || "";
  const { signals, counts } = await api(`/signals?kind=${kind}`);
  $("#view").innerHTML = `<div class="ph"><div><h1>Signals</h1><p>What happened after you reached out: replies, bounces, people who changed jobs, and new contacts found along the way.</p></div></div>
  <div class="tabs"><a class="tab ${!kind ? "on" : ""}" href="#/signals">All</a>${Object.entries(SIG_LABEL).map(([k, v]) => `<a class="tab ${kind === k ? "on" : ""}" href="#/signals?kind=${k}">${v} <span class="n">${counts[k] || 0}</span></a>`).join("")}</div>
  <div class="card">${signals.length ? `<ul class="feed">${signals.map((s) => `<li><span class="sig ${s.kind}">${SIG_LABEL[s.kind] || s.kind}</span><span><span class="mono">${esc(s.email || "")}</span><div class="faint" style="font-size:12px">${esc(s.detail || "")}</div></span><span class="when">${when(s.at)}</span></li>`).join("")}</ul>` : `<div class="empty"><h3>No signals yet</h3><p>Connect the mailbox your sequences send from, then run a sequence.</p><a class="btn primary" href="#/contribute">${icon("mail")} Connect mailbox</a></div>`}</div>`;
};

/* ---------- API keys ---------- */
views.api = async () => {
  const [{ api_keys }, cu] = await Promise.all([api("/auth/api_keys"), api("/usage_stats/credit_usage")]);
  const first = (() => { try { return localStorage.getItem("gc_first_key"); } catch { return null; } })();
  const base = location.origin + "/api/v1";
  $("#view").innerHTML = `<div class="ph"><div><h1>API & credits</h1><p>Endpoints and filters match Apollo's, so existing scripts work by changing the base URL. <a href="/docs" target="_blank">Full reference</a></p></div><div class="ph-actions"><button class="btn primary" id="newk">${icon("plus")} Create key</button></div></div>
  ${first ? `<div class="keybox"><b>Your master key</b><code>${esc(first)}</code><button class="btn sm" id="ck">${icon("copy")} Copy</button><button class="btn sm ghost" id="hk">I've saved it</button><span class="muted" style="font-size:12px">Shown once.</span></div>` : ""}
  <div class="stats"><div><b>${fmt(cu.used)}</b><span>Credits used this month</span></div><div><b>${fmt(cu.remaining)}</b><span>Remaining</span></div>${Object.entries(cu.costs).map(([k, v]) => `<div><b>${v}</b><span>Credits per ${k}</span></div>`).join("")}</div>
  <div class="grid2"><div class="card"><h2>Keys</h2><div class="tablewrap" style="border:0"><table class="dt" style="min-width:0"><thead><tr><th>Label</th><th>Key</th><th>Access</th><th>Last used</th><th></th></tr></thead><tbody>${api_keys.map((k) => `<tr><td>${esc(k.label)}</td><td class="mono">${esc(k.prefix)}</td><td>${k.is_master ? "Master" : "Search & enrich"}</td><td class="mono faint">${when(k.last_used_at)}</td><td style="text-align:right"><button class="btn sm ghost" data-rev="${k.id}">Revoke</button></td></tr>`).join("")}</tbody></table></div></div>
  <div class="card"><h2>Try it</h2><pre class="code"># search people (free, no emails)
curl -X POST "${base}/mixed_people/api_search?person_titles[]=CEO&person_locations[]=India" \\
  -H "x-api-key: $KEY"

# find one email (1 credit)
curl -X POST "${base}/people/match?first_name=Jane&last_name=Doe&domain=acme.com" \\
  -H "x-api-key: $KEY"

# company format
curl -X POST "${base}/organizations/enrich?domain=stripe.com" -H "x-api-key: $KEY"</pre></div></div>`;
  $("#newk").onclick = async () => { const f = await dialog({ title: "Create API key", ok: "Create key", fields: [{ name: "label", label: "Label", value: "integration" }, { name: "is_master", type: "checkbox", text: "Master key (sequences, users, usage)" }] }); if (!f) return; const r = await post("/auth/api_keys", f); await dialog({ title: "Copy your key", body: `<code style="word-break:break-all">${esc(r.api_key)}</code><br><br>It won't be shown again.`, ok: "Done" }); views.api(); };
  $$("[data-rev]").forEach((b) => (b.onclick = async () => { if (await confirmDlg("Revoke key", "Scripts using it will stop working.", "Revoke", true)) { await del(`/auth/api_keys/${b.dataset.rev}`); views.api(); } }));
  $("#ck") && ($("#ck").onclick = () => navigator.clipboard.writeText(first).then(() => toast("Key copied")));
  $("#hk") && ($("#hk").onclick = () => { try { localStorage.removeItem("gc_first_key"); } catch {} views.api(); });
};

/* ---------- Data ---------- */
views.data = async () => {
  const s = await api("/stats");
  const bars = (obj, map = {}) => { const e = Object.entries(obj).sort((a, b) => b[1] - a[1]); const max = Math.max(1, ...e.map((x) => x[1])); return `<div class="bars">${e.map(([k, v]) => `<div class="row"><span>${esc(map[k] || k || "Unknown")}</span><span class="track"><i style="width:${(v / max) * 100}%"></i></span><span class="v">${fmt(v)}</span></div>`).join("")}</div>`; };
  $("#view").innerHTML = `<div class="ph"><div><h1>Data library</h1><p>Every record keeps its source. Grow the library with the commands below.</p></div></div>
  <div class="lib"><div><b>${fmt(s.people)}</b><span>People</span></div><div><b>${fmt(s.organizations)}</b><span>Companies</span></div><div><b>${fmt(s.people_with_email)}</b><span>People with email</span><div class="meter"><i style="width:${s.people ? (s.people_with_email / s.people) * 100 : 0}%"></i></div></div><div><b>${fmt(s.orgs_with_domain)}</b><span>Companies with website</span><div class="meter"><i style="width:${s.organizations ? (s.orgs_with_domain / s.organizations) * 100 : 0}%"></i></div></div></div>
  <div class="grid3"><div class="card"><h2>People by source</h2>${bars(s.people_by_source, SRC)}</div><div class="card"><h2>Companies by source</h2>${bars(s.orgs_by_source, SRC)}</div><div class="card"><h2>Companies by country</h2>${bars(Object.fromEntries(s.orgs_by_country.map((r) => [r.country, r.n])))}</div></div>
  <div class="card" style="margin-top:14px"><h2>Email status</h2>${bars(s.email_status, STATUS)}</div>
  <div class="card"><h2>Import runs</h2><div class="tablewrap" style="border:0"><table class="dt"><thead><tr><th>Source</th><th>Status</th><th>Rows</th><th>Companies added</th><th>People added</th><th>Started</th></tr></thead><tbody>${s.ingest_runs.map((r) => `<tr><td>${esc(SRC[r.source] || r.source)}</td><td><span class="status"><span class="dot st-${r.status === "done" ? "verified" : r.status === "failed" ? "invalid" : "guessed"}"></span>${esc(r.status)}</span>${r.error ? `<div class="sub" style="color:var(--red)">${esc(r.error).slice(0, 90)}</div>` : ""}</td><td class="mono">${fmt(r.rows_in)}</td><td class="mono">${fmt(r.orgs)}</td><td class="mono">${fmt(r.people)}</td><td class="mono faint">${when(r.started)}</td></tr>`).join("")}</tbody></table></div></div>
  <div class="card"><h2>Grow the library</h2><pre class="code">python -m ingest.run sec_insiders --quarters 8   # officers & directors
python -m ingest.run sec_formd --quarters 8      # private-company executives
python -m ingest.run wikidata                     # global companies + leadership
python -m ingest.run gleif --country IN           # registered entities by country
python -m ingest.run companies_house --active-only
python -m ingest.run webcrawl --from-db 500       # company team pages
python -m ingest.run guess_emails && python -m ingest.run verify_emails</pre></div>`;
};

/* ---------- Home ---------- */
const PRESETS = [
  ["CFOs at public companies", "people", { person_titles: ["Chief Financial"] }],
  ["Founders", "people", { person_seniorities: ["founder"] }],
  ["Directors in New York", "people", { person_seniorities: ["director"], person_locations: ["NY"] }],
  ["Executives with verified email", "people", { person_seniorities: ["c_suite", "vp"], contact_email_status: ["verified"] }],
  ["Companies in India", "companies", { organization_locations: ["IN"] }],
];
views.home = async () => {
  const [s, cs, accts, contacts, seqs, sig] = await Promise.all([api("/stats"), api("/contribute/stats"), api("/mail_accounts"), api("/contacts?per_page=1"), api("/sequences"), api("/signals?limit=8")]);
  const h = new Date().getHours();
  const name = (state.user.name || state.user.email.split("@")[0]).split(" ")[0];
  const steps = [
    ["Access your first email", contacts.pagination.total_entries > 0, "#/people"],
    ["Turn on contact sharing", cs.contribute, "#/contribute"],
    ["Connect your mailbox", accts.accounts.length > 0, "#/contribute"],
    ["Create a sequence with steps", seqs.sequences.some((x) => x.steps.length), "#/sequences"],
    ["Get your first reply", (sig.counts.reply || 0) > 0, "#/signals"],
  ];
  const done = steps.filter((x) => x[1]).length;
  $("#view").innerHTML = `<p class="muted" style="margin:0">${h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"}</p><h1 class="hello">${esc(name)}, who are you looking for?</h1>
  <form class="bigsearch" id="hs"><label class="gsearch">${icon("search")}<input name="q" placeholder="Try “head of sales” or “Udacity”" aria-label="Search people"></label><button class="btn primary">Search</button></form>
  <div class="presets">${PRESETS.map((p, i) => `<button class="pill" data-preset="${i}">${esc(p[0])}</button>`).join("")}</div>
  <div class="lib"><div><b>${fmt(s.people)}</b><span>People in library</span></div><div><b>${fmt(s.organizations)}</b><span>Companies</span></div><div><b>${fmt(cs.network.verified_emails)}</b><span>Verified emails</span></div><div><b>${fmt(contacts.pagination.total_entries)}</b><span>Your contacts</span></div></div>
  <div class="home"><div class="card"><h2>Recent signals <a href="#/signals" style="font-weight:500;font-size:13px">View all</a></h2>${sig.signals.length ? `<ul class="feed">${sig.signals.map((x) => `<li><span class="sig ${x.kind}">${SIG_LABEL[x.kind] || x.kind}</span><span><span class="mono">${esc(x.email || "")}</span><div class="faint" style="font-size:12px">${esc(x.detail || "")}</div></span><span class="when">${when(x.at)}</span></li>`).join("")}</ul>` : '<p class="muted">Replies, bounces and job changes from your outreach show up here.</p>'}</div>
  <div class="card"><h2>Get set up <span class="mono faint" style="font-weight:400">${done}/${steps.length}</span></h2><div class="meter" style="margin:-4px 0 8px"><i style="width:${(done / steps.length) * 100}%"></i></div><ul class="steps">${steps.map(([t, ok, href]) => `<li class="${ok ? "done" : ""}"><span class="tick">${ok ? icon("check") : ""}</span><span class="t">${t}</span>${ok ? "" : `<a class="btn sm" href="${href}">Start</a>`}</li>`).join("")}</ul></div></div>`;
  $("#hs").onsubmit = (e) => { e.preventDefault(); globalSearch(e.target.q.value); };
  $$("[data-preset]").forEach((b) => (b.onclick = () => { const [, where, f] = PRESETS[+b.dataset.preset]; state[where === "people" ? "p" : "c"] = { filters: f, page: 1, tab: "all" }; location.hash = "#/" + where; }));
};
function globalSearch(q) {
  q = (q || "").trim();
  state.p = { filters: q ? { q_keywords: q } : {}, page: 1, tab: "all" };
  if (location.hash === "#/people") views.people(); else location.hash = "#/people";
}

/* ---------- auth ---------- */
function showAuth(mode = "login") {
  $("#shell").classList.add("hidden");
  const a = $("#auth");
  a.classList.remove("hidden");
  const demo = [["Asha Verma", "VP Engineering · Northwind Labs", "asha.verma@northwind-labs.example"], ["Daniel Okafor", "Head of Sales · Brightwave Systems", "d.okafor@brightwave-systems.example"], ["Meera Iyer", "Chief Financial Officer · Harbor & Pine", "meera@harborpine.example"]];
  a.innerHTML = `<section class="auth-art"><span class="rail-logo">gc</span><div><h1>Find the person behind the company.</h1><p>Search executives from public filings and contributed business contacts, get their work email, and run outreach from your own server.</p></div>
  <div class="cards" aria-hidden="true">${demo.map((d, i) => `<div class="pcard">${avatar(d[0])}<div class="t"><b>${d[0]}</b><span>${d[1]}</span></div><span data-demo="${i}"><span class="reveal"><span class="bar"></span></span></span></div>`).join("")}</div></section>
  <section class="auth-form"><form id="af" novalidate><h2>${mode === "login" ? "Log in" : "Create your account"}</h2><p class="muted" style="margin:0 0 20px">${mode === "login" ? "Welcome back." : "Free, with no credit card and no seat limits."}</p>
  ${mode === "signup" ? `<label class="fld"><span>Name</span><input name="name" autocomplete="name"></label>` : ""}<label class="fld"><span>Work email</span><input name="email" type="email" autocomplete="email" required></label><label class="fld"><span>Password</span><input name="password" type="password" autocomplete="${mode === "login" ? "current-password" : "new-password"}" minlength="8" required placeholder="${mode === "signup" ? "At least 8 characters" : ""}"></label>
  <button class="btn primary" style="width:100%;justify-content:center;height:40px">${mode === "login" ? "Log in" : "Create account"}</button><div class="err" id="aerr"></div>
  <p class="switchmode">${mode === "login" ? `New here? <button type="button" data-m="signup">Create an account</button>` : `Already have an account? <button type="button" data-m="login">Log in</button>`}</p></form></section>`;
  $("[data-m]", a).onclick = (e) => showAuth(e.target.dataset.m);
  $("#af").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    if (!f.email || !f.password) return ($("#aerr").textContent = "Enter your work email and password.");
    if (mode === "signup" && f.password.length < 8) return ($("#aerr").textContent = "Use at least 8 characters for the password.");
    try {
      const r = await fetch(`${API}/auth/${mode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(f), credentials: "same-origin" });
      const j = await r.json();
      if (!r.ok) { const d = j.detail; $("#aerr").textContent = d?.error === "bad_credentials" ? "That email and password don't match." : d?.error === "email_taken" ? "An account with this email already exists. Log in instead." : Array.isArray(d) ? "Enter a valid work email." : "Something went wrong. Try again."; return; }
      if (j.api_key) try { localStorage.setItem("gc_first_key", j.api_key); } catch {}
      await boot();
    } catch { $("#aerr").textContent = "Can't reach the server. Check that it's running."; }
  };
  $("input", a).focus();
  // signature demo: unmask each card's email in turn
  demo.forEach((d, i) => setTimeout(() => { const el = $(`[data-demo="${i}"]`); if (el) el.innerHTML = `<span class="email unmask"><span class="dot st-verified"></span><span class="addr">${d[2]}</span></span>`; }, 900 + i * 700));
}

/* ---------- shell + router ---------- */
const NAV = [["home", "Home", "home"], ["people", "People", "people"], ["companies", "Companies", "building"], ["sep"], ["contacts", "Contacts", "contact"], ["lists", "Lists", "list"], ["sequences", "Sequences", "send"], ["signals", "Signals", "radar"], ["sep"], ["enrich", "Enrich", "bolt"], ["contribute", "Contribute", "share"], ["spacer"], ["data", "Data library", "chart"], ["api", "API & credits", "key"]];
function renderShell() {
  $("#rail").innerHTML = `<span class="rail-logo" title="getcontact">gc</span>${NAV.map(([k, t, ic]) => (k === "sep" ? '<span class="sep"></span>' : k === "spacer" ? '<span class="spacer"></span>' : `<a href="#/${k}" data-nav="${k}" aria-label="${t}">${icon(ic)}<span class="tip">${t}</span></a>`)).join("")}`;
  const u = state.user;
  $("#me").textContent = initials(u.name || u.email);
  $("#me").setAttribute("aria-label", `Account menu for ${u.email}`);
  $("#meHead").innerHTML = `<b>${esc(u.name || u.email.split("@")[0])}</b>${esc(u.email)}`;
}
async function refreshCredits() {
  try { const r = await api("/auth/me"); state.credits = r.credits; $("#credits").textContent = `${fmt(r.credits.used)} credits used`; } catch {}
}
function route() {
  const name = (location.hash.replace("#/", "") || "home").split("?")[0];
  const v = views[name] ? name : "home";
  $$(".rail a").forEach((a) => { const on = a.dataset.nav === v; a.classList.toggle("active", on); on ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"); });
  state.bulk = null; state.sel.clear(); updateBulk(); closeDrawer();
  document.title = `${(NAV.find((n) => n[0] === v) || [, "Home"])[1]} · getcontact`;
  Promise.resolve(views[v]()).catch((e) => { if (!/session/.test(e.message)) $("#view").innerHTML = `<div class="empty"><h3>This page didn't load</h3><p>${esc(e.message)}</p><button class="btn" onclick="route()">Try again</button></div>`; });
  $("#view").focus({ preventScroll: true });
}
window.addEventListener("hashchange", route);

/* ---------- global delegated events ---------- */
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-reveal],[data-open-person],[data-open-company],[data-copy],[data-bulk]");
  if (!t) { if (!e.target.closest("#me,#meMenu")) $("#meMenu").classList.add("hidden"); return; }
  if (t.dataset.reveal) { e.stopPropagation(); revealPerson(+t.dataset.reveal).then((p) => p && toast(p.email ? "Email accessed · saved to Contacts" : "No email found · no credit used")); }
  else if (t.dataset.openPerson) personDrawer(+t.dataset.openPerson);
  else if (t.dataset.openCompany) companyDrawer(+t.dataset.openCompany);
  else if (t.dataset.copy) navigator.clipboard.writeText(t.dataset.copy).then(() => toast("Email copied"));
  else if (t.dataset.bulk) onBulk(t.dataset.bulk);
});
document.addEventListener("change", (e) => {
  if (e.target.matches("[data-sel]")) { const id = +e.target.dataset.sel; e.target.checked ? state.sel.add(id) : state.sel.delete(id); updateBulk(); }
  if (e.target.matches("[data-selall]")) { $$("[data-sel]").forEach((c) => { c.checked = e.target.checked; const id = +c.dataset.sel; e.target.checked ? state.sel.add(id) : state.sel.delete(id); }); updateBulk(); }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeDrawer(); $("#meMenu").classList.add("hidden"); }
  if (e.key === "/" && !e.target.matches("input,textarea,select") && !$("#shell").classList.contains("hidden")) { e.preventDefault(); $("#gq").focus(); }
});
$("#gsearch").onsubmit = (e) => { e.preventDefault(); globalSearch($("#gq").value); $("#gq").blur(); };
$("#me").onclick = () => $("#meMenu").classList.toggle("hidden");
$("#logout").onclick = async () => { await post("/auth/logout"); state.user = null; showAuth(); };

async function boot() {
  try {
    const r = await fetch(`${API}/auth/me`, { credentials: "same-origin" });
    if (!r.ok) return showAuth();
    const j = await r.json();
    state.user = j.user; state.credits = j.credits;
  } catch { return showAuth(); }
  $("#auth").classList.add("hidden");
  $("#shell").classList.remove("hidden");
  renderShell();
  $("#credits").textContent = `${fmt(state.credits.used)} credits used`;
  route();
}
boot();
