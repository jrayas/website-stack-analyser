#!/usr/bin/env python3
"""
Export website_analysis.db into static JSON files for the docs/ static site.

Usage:
    python export_static.py

Reads every site and its runs from the database and writes:
    docs/data/index.json          - list of all sites (slug, url, latest run date, run count)
    docs/data/<slug>.json         - full history for one site (all runs, each with its
                                     dependencies, uncertainties, js_dependencies, design_tokens)

The frontend (docs/app.js) fetches these at runtime based on the URL slug, so the site
stays a plain static site with no server-side database access needed.

Run this after every `log_run.py` call so the deployed site reflects the latest data.
"""

import json
import re
import shutil
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = Path(__file__).parent / "website_analysis.db"
DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"
DOCS_REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"


def slugify_url(url: str) -> str:
    host = urlparse(url).netloc or url
    host = host.lower()
    return re.sub(r"[^a-z0-9.\-]", "_", host)


def fetch_run_children(conn: sqlite3.Connection, run_id: int) -> dict:
    deps = [
        dict(row)
        for row in conn.execute(
            "SELECT layer, technology, version, evidence, confidence FROM dependencies WHERE run_id = ?",
            (run_id,),
        )
    ]
    uncertainties = [
        dict(row)
        for row in conn.execute(
            "SELECT question, evidence_needed FROM uncertainties WHERE run_id = ?", (run_id,)
        )
    ]
    js_deps = [
        dict(row)
        for row in conn.execute(
            "SELECT layer, npm_package, suggested_version, description, evidence_confidence, "
            "alternative_package, learn_url FROM js_dependencies WHERE run_id = ?",
            (run_id,),
        )
    ]
    design_tokens = [
        dict(row)
        for row in conn.execute(
            "SELECT category, property, value, evidence, confidence FROM design_tokens WHERE run_id = ?",
            (run_id,),
        )
    ]
    return {
        "dependencies": deps,
        "uncertainties": uncertainties,
        "js_dependencies": js_deps,
        "design_tokens": design_tokens,
    }


def copy_report(report_path: str) -> str | None:
    """Copy website/<host>/<date>.md into docs/reports/<host>/<date>.md so GitHub
    Pages (which only serves docs/) can link to it. Returns the docs-relative path."""
    src = PROJECT_ROOT / report_path
    if not src.exists():
        return None
    rel = Path(report_path)
    # report_path is like "website/<host>/<date>.md" -> reports/<host>/<date>.md
    dest_rel = Path("reports") / Path(*rel.parts[1:])
    dest = PROJECT_ROOT / "docs" / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return str(dest_rel).replace("\\", "/")


def export_static(db_path: Path = DB_PATH, out_dir: Path = DOCS_DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    sites = [dict(row) for row in conn.execute("SELECT id, url, first_seen, notes FROM sites ORDER BY url")]

    index_entries = []
    for site in sites:
        slug = slugify_url(site["url"])
        runs = [
            dict(row)
            for row in conn.execute(
                "SELECT id, access_date, pages_examined, limitations, overview, report_path "
                "FROM analysis_runs WHERE site_id = ? ORDER BY access_date DESC",
                (site["id"],),
            )
        ]
        for run in runs:
            run.update(fetch_run_children(conn, run["id"]))
            run["report_url"] = copy_report(run["report_path"])

        site_doc = {
            "slug": slug,
            "url": site["url"],
            "first_seen": site["first_seen"],
            "notes": site["notes"],
            "runs": runs,
        }
        with open(out_dir / f"{slug}.json", "w", encoding="utf-8") as f:
            json.dump(site_doc, f, indent=2)

        index_entries.append(
            {
                "slug": slug,
                "url": site["url"],
                "run_count": len(runs),
                "latest_access_date": runs[0]["access_date"] if runs else None,
            }
        )

    index_entries.sort(key=lambda e: e["slug"])
    with open(out_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index_entries, f, indent=2)

    conn.close()
    print(f"Exported {len(sites)} site(s) to {out_dir}")


if __name__ == "__main__":
    export_static()
