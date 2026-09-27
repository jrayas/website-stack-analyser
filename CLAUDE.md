# Website Stack Analyser — Project Instructions

This project reverse-engineers a target website's public tech stack (frontend, backend, CMS,
hosting, JS dependencies, etc.) well enough to recreate it with an equivalent stack. Full rules
and required output format are in `prompt.md`. Full file/DB workflow is in `README.md`. Read
both before running an analysis if this is a fresh session.

## Trigger

When a user message contains the line:

```
site: <site>
```

treat `<site>` as the analysis target and proceed with the full workflow below immediately,
without asking for confirmation first. `<site>` may be a bare domain or a full URL.

## Workflow to run on trigger

1. Derive the host name from `<site>`: lowercase, strip protocol/path/query, replace any
   character outside `[a-z0-9.-]` with `_`.
2. Gather public evidence only (HTML, headers, scripts, CSP, meta tags, robots.txt, source maps
   if publicly exposed). Never bypass auth or access controls.
3. Fill in a report using `website.md`'s current template structure exactly, including:
   - Site Overview
   - Dependency and Technology Inventory table
   - Evidence and Uncertainties
   - Recreation Guidance
   - Suggested package.json Dependencies table (npm package, suggested version, description,
     evidence/confidence, alternative package, website to learn) — clearly marked as a
     recommendation, not a confirmed fact about the real site's actual `package.json`.
   - Visual Design System table (Typography / Colour / Layout / Other — property, value,
     evidence, confidence) extracted from public CSS/HTML: fonts, colour palette, layout and
     spacing rules. Never used to store or reproduce copyrighted logos/illustrations/imagery —
     system-level design tokens only.
4. Save the completed report to `website/<host>/<YYYY-MM-DD>.md` (today's date). Never overwrite
   an existing dated report for that host.
5. Log the findings to `database/website_analysis.db` by writing a JSON file matching the shape
   documented in `database/log_run.py`'s docstring, then running:
   ```
   python database/log_run.py <run.json>
   ```
   Do NOT write ad-hoc SQL/sqlite3 Python for this — `log_run.py` is the single point of entry:
   it validates every `layer` against the `layers` table and every `confidence` value before
   writing anything, reuses an existing `sites` row by URL, and commits the whole run as one
   transaction. It fills `sites`, `analysis_runs`, `dependencies`, `uncertainties`,
   `js_dependencies` (the package.json table), and `design_tokens` (the visual design system
   table) in one call.
6. Run `python database/export_static.py` to regenerate `docs/data/*.json` and copy the new
   report into `docs/reports/` so the deployed static site reflects this run.
7. Commit and push (`git add -A && git commit && git push`) so GitHub Pages picks up the
   update. The site is deployed at whatever URL `gh api repos/<owner>/<repo>/pages` reports
   (GitHub Pages serving `docs/` on the default branch).
6. Reset `website.md` back to its blank template afterwards, if it was used as scratch space for
   this run.
7. Report back to the user: report file path, top findings with confidence, DB row counts.

## Accuracy rules (from prompt.md, non-negotiable)

- Never invent a package name, version, or fact. Use "unknown" and state what evidence would
  confirm it.
- A framework fingerprint or CDN hostname does not prove the full dependency list or the backend.
- Distinguish direct observation from deduction in every finding.
- Suggested/recommended dependency choices must be explicitly labeled as recommendations, not
  claims about the original site's real stack.
