/* Reads what the user is currently viewing (page title / h1 / meta) and looks it up in getcontact.
   It does not crawl or scrape beyond the visible page the user opened. */
const $ = (s) => document.querySelector(s);
let cfg = { base: "http://localhost:8000", key: "" };

chrome.storage.local.get(["gc"], (r) => {
  if (r.gc) cfg = r.gc;
  $("#base").value = cfg.base; $("#key").value = cfg.key;
  if (cfg.key) showMain();
});
$("#save").onclick = () => { cfg = { base: $("#base").value.replace(/\/$/, ""), key: $("#key").value.trim() }; chrome.storage.local.set({ gc: cfg }); showMain(); };
$("#cfg").onclick = () => { $("#setup").style.display = ""; $("#main").style.display = "none"; };

async function showMain() {
  $("#setup").style.display = "none"; $("#main").style.display = "";
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    const [{ result }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => ({
      title: document.title, h1: document.querySelector("h1")?.innerText?.trim() || "",
      og: document.querySelector('meta[property="og:site_name"]')?.content || "", host: location.hostname.replace(/^www\./, ""), url: location.href,
    }) });
    const t = result.title || "";
    if (result.host.includes("linkedin.com") && result.url.includes("/in/")) {
      // "Name - Title - Company | LinkedIn"  or "Name | LinkedIn"
      const parts = t.replace(/\s*\|\s*LinkedIn.*$/, "").split(" - ").map((s) => s.trim());
      $("#name").value = result.h1 || parts[0] || ""; $("#title").value = parts[1] || ""; $("#company").value = parts[2] || "";
    } else if (result.host.includes("linkedin.com") && result.url.includes("/company/")) {
      $("#company").value = result.h1 || t.split("|")[0].trim();
    } else {
      $("#company").value = result.og || result.h1 || t.split(/[|–-]/)[0].trim(); $("#domain").value = result.host;
    }
  } catch (e) { $("#out").textContent = "Cannot read this page: " + e.message; }
}

async function call(path, method = "POST", body) {
  const r = await fetch(cfg.base + "/api/v1" + path, { method, headers: { "x-api-key": cfg.key, "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  return r.json();
}
const split = (n) => { const p = n.trim().split(/\s+/); return [p[0] || "", p.slice(1).join(" ")]; };

$("#find").onclick = async () => {
  const [first_name, last_name] = split($("#name").value);
  const q = new URLSearchParams({ first_name, last_name, organization_name: $("#company").value, domain: $("#domain").value });
  if (!first_name && $("#domain").value) { $("#out").textContent = JSON.stringify(await call(`/organizations/enrich?domain=${encodeURIComponent($("#domain").value)}`), null, 2); return; }
  const r = await call(`/people/match?${q}`);
  $("#out").textContent = r.person ? `${r.person.name}\n${r.person.email || "no email"} (${r.person.email_status})\nconfidence: ${r.match_confidence}` : "Not found in library. Add a domain to generate a pattern-based email.";
};
$("#add").onclick = async () => {
  const [first_name, last_name] = split($("#name").value);
  const r = await call("/people", "POST", { first_name, last_name, title: $("#title").value, organization_name: $("#company").value, domain: $("#domain").value });
  if (r.person) { await call("/contacts", "POST", { person_id: r.person.id }); $("#out").textContent = "Saved: " + r.person.name + (r.person.email ? "\n" + r.person.email : ""); }
  else $("#out").textContent = JSON.stringify(r, null, 2);
};
