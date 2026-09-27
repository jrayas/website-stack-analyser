// Website Stack Analyser — static frontend
// Reads docs/data/*.json (exported by database/export_static.py) and renders
// either the site list (index.html) or one site's report (site.html?slug=<slug>).

const CONFIDENCE_CLASS = { High: "conf-high", Medium: "conf-medium", Low: "conf-low" };

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function confBadge(confidence) {
  const cls = CONFIDENCE_CLASS[confidence] || "conf-unknown";
  return `<span class="badge ${cls}">${escapeHtml(confidence || "Unknown")}</span>`;
}

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}

function renderSiteList(entries) {
  const el = document.getElementById("site-list");
  if (!entries.length) {
    el.innerHTML = `<p class="loading">No sites analysed yet.</p>`;
    return;
  }
  el.innerHTML = entries
    .map(
      (e) => `
      <a class="site-card" href="site.html?slug=${encodeURIComponent(e.slug)}">
        <h2>${escapeHtml(e.url)}</h2>
        <p>${e.run_count} run${e.run_count === 1 ? "" : "s"} &middot; latest ${escapeHtml(e.latest_access_date || "—")}</p>
      </a>`
    )
    .join("");
}

function depTable(rows, columns) {
  if (!rows.length) return `<p class="empty">None recorded.</p>`;
  const head = columns.map((c) => `<th>${escapeHtml(c.label)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${columns
          .map((c) => {
            const v = row[c.key];
            if (c.key === "confidence" || c.key === "evidence_confidence") {
              return `<td>${confBadge(v)}</td>`;
            }
            return `<td>${escapeHtml(v)}</td>`;
          })
          .join("")}</tr>`
    )
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderRun(run) {
  const container = document.getElementById("report");
  container.innerHTML = `
    <section class="block">
      <h3>Site Overview</h3>
      <p><strong>Access date:</strong> ${escapeHtml(run.access_date)}</p>
      <p><strong>Pages examined:</strong> ${escapeHtml(run.pages_examined)}</p>
      <p><strong>Limitations:</strong> ${escapeHtml(run.limitations)}</p>
      <p><strong>Overview:</strong> ${escapeHtml(run.overview)}</p>
      <p>${
        run.report_url
          ? `<a href="${escapeHtml(run.report_url)}" target="_blank" rel="noopener">View full markdown report &rarr;</a>`
          : `<span class="note">Report file not found.</span>`
      }</p>
    </section>

    <section class="block">
      <h3>Dependency and Technology Inventory</h3>
      ${depTable(run.dependencies, [
        { key: "layer", label: "Layer" },
        { key: "technology", label: "Technology" },
        { key: "version", label: "Version" },
        { key: "evidence", label: "Evidence" },
        { key: "confidence", label: "Confidence" },
      ])}
    </section>

    <section class="block">
      <h3>Uncertainties</h3>
      ${depTable(run.uncertainties, [
        { key: "question", label: "Question" },
        { key: "evidence_needed", label: "Evidence needed" },
      ])}
    </section>

    <section class="block">
      <h3>Suggested package.json Dependencies</h3>
      <p class="note">Recommendation only — not a confirmed fact about the real site's package.json.</p>
      ${depTable(run.js_dependencies, [
        { key: "layer", label: "Layer" },
        { key: "npm_package", label: "npm package" },
        { key: "suggested_version", label: "Version" },
        { key: "description", label: "Description" },
        { key: "evidence_confidence", label: "Evidence / Confidence" },
        { key: "alternative_package", label: "Alternative" },
        { key: "learn_url", label: "Learn more" },
      ])}
    </section>

    <section class="block">
      <h3>Visual Design System</h3>
      ${depTable(run.design_tokens, [
        { key: "category", label: "Category" },
        { key: "property", label: "Property" },
        { key: "value", label: "Value" },
        { key: "evidence", label: "Evidence" },
        { key: "confidence", label: "Confidence" },
      ])}
    </section>
  `;
}

function renderTabs(runs, onSelect) {
  const tabsEl = document.getElementById("run-tabs");
  if (runs.length <= 1) {
    tabsEl.innerHTML = "";
    return;
  }
  tabsEl.innerHTML = runs
    .map((r, i) => `<button class="tab${i === 0 ? " active" : ""}" data-index="${i}">${escapeHtml(r.access_date)}</button>`)
    .join("");
  tabsEl.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      tabsEl.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      onSelect(runs[Number(btn.dataset.index)]);
    });
  });
}

async function initIndexPage() {
  try {
    const entries = await loadJson("data/index.json");
    renderSiteList(entries);
  } catch (err) {
    document.getElementById("site-list").innerHTML = `<p class="error">Failed to load site list: ${escapeHtml(err.message)}</p>`;
  }
}

async function initSitePage() {
  const params = new URLSearchParams(window.location.search);
  const slug = params.get("slug");
  const titleEl = document.getElementById("site-title");
  const reportEl = document.getElementById("report");

  if (!slug) {
    titleEl.textContent = "No site specified";
    reportEl.innerHTML = `<p class="error">Missing ?slug= in the URL.</p>`;
    return;
  }

  try {
    const site = await loadJson(`data/${slug}.json`);
    titleEl.textContent = site.url;
    if (!site.runs.length) {
      reportEl.innerHTML = `<p class="empty">No runs recorded for this site.</p>`;
      return;
    }
    renderTabs(site.runs, renderRun);
    renderRun(site.runs[0]);
  } catch (err) {
    titleEl.textContent = slug;
    reportEl.innerHTML = `<p class="error">Failed to load report: ${escapeHtml(err.message)}</p>`;
  }
}

if (document.getElementById("site-list")) {
  initIndexPage();
} else if (document.getElementById("report")) {
  initSitePage();
}
