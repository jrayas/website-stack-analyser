# Website Stack Analyser — Workflow

## Files

| Path | Purpose |
|---|---|
| `prompt.md` | Analysis instructions (rules, process, required output format). |
| `website.md` | Scratch template at root — paste a site here to start a run. Reset to blank after each run. |
| `website/<host>/<date>.md` | Saved human-readable report for one run. One file per run date — never overwritten. |
| `database/schema.sql` | SQLite schema. |
| `database/website_analysis.db` | Logged structured results (queryable across all sites/runs). |
| `database/log_run.py` | The only script that writes to the database. Takes one run as a JSON file. |
| `database/export_static.py` | Exports the database to `docs/data/*.json` and copies reports into `docs/reports/` for the deployed static site. |
| `docs/` | Static site (GitHub Pages), lists analysed sites and renders each report by slug (`site.html?slug=<slug>`). Deployed at https://jrayas.github.io/website-stack-analyser/ |

## Workflow

1. Paste the target site (URL, or URL + any details) into `website.md`.
2. Analysis is run following `prompt.md`'s rules (public evidence only, cite everything, rate confidence).
3. Host name is derived from the URL, sanitised for use as a folder name:
   lowercased, protocol/path/query stripped, non `[a-z0-9.-]` characters replaced with `_`.
   Example: `https://Shop.Example.com/page?x=1` → `shop.example.com`.
4. The filled-in report is saved to `website/<host>/<YYYY-MM-DD>.md` (today's date).
   If that host already has earlier reports, they are kept — nothing is overwritten.
5. The same findings are logged to `database/website_analysis.db` by writing a JSON file
   (see the docstring in `database/log_run.py` for the exact shape) and running:
   ```
   python database/log_run.py <run.json>
   ```
   This is the only way runs should be written to the database — it validates every `layer`
   against the fixed `layers` table and every `confidence` value before writing anything, and
   commits all rows for the run in a single transaction (all or nothing). It fills:
   - `sites` — one row per host (`url` is `UNIQUE`, reused automatically on re-analysis)
   - `analysis_runs` — one row per run, linked to the site and to the saved report's path
   - `dependencies` — one row per stack layer/technology found
   - `uncertainties` — one row per open question
   - `js_dependencies` — one row per suggested npm package (mirrors website.md's
     "Suggested package.json Dependencies" table)
   - `design_tokens` — one row per font/colour/layout finding (mirrors website.md's
     "Visual Design System" table). `category` must be Typography, Colour, Layout, or Other.
     Describes the design *system* only — never used to store or reproduce copyrighted
     logos/illustrations/imagery.
6. `website.md` is reset back to the blank template, ready for the next site.
7. `python database/export_static.py` regenerates the static site's data, then commit and push
   so GitHub Pages redeploys automatically.

## Deployment

Repo: https://github.com/jrayas/website-stack-analyser (public)
Live site: https://jrayas.github.io/website-stack-analyser/ (GitHub Pages, serves `docs/` from `master`)

## Rules that must hold

- Any script touching the database must run `PRAGMA foreign_keys = ON;` first — SQLite does not enforce foreign keys by default.
- Never invent a fact to fill a table cell; use "unknown" and say what evidence would confirm it.
- Historical reports for a site are never deleted or overwritten — each run gets its own dated file.
