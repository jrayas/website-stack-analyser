#!/usr/bin/env python3
"""
Log one website analysis run into database/website_analysis.db from a JSON file.

Usage:
    python log_run.py <run.json>

Purpose: this is the ONE place that writes to the database, so a run never has
to be logged with hand-written ad-hoc SQL. Feed it a JSON file describing the
run and it does the rest: reuses the site row if the URL was seen before,
validates every `layer` against the fixed `layers` table, validates confidence
values, and writes everything in a single transaction (all rows or none).

Expected JSON shape:
{
  "site_url": "https://example.com",
  "report_path": "website/example.com/2026-09-27.md",
  "access_date": "2026-09-27",              // optional, defaults to now
  "pages_examined": "...",                  // optional
  "limitations": "...",                     // optional
  "overview": "...",                        // optional

  "dependencies": [
    {
      "layer": "Frontend framework",        // must exist in the layers table
      "technology": "Next.js",
      "version": "Unknown",                 // optional
      "evidence": "...",
      "confidence": "High"                  // High | Medium | Low
    }
  ],

  "uncertainties": [
    {
      "question": "...",
      "evidence_needed": "..."              // optional
    }
  ],

  "js_dependencies": [                      // optional, mirrors website.md's
    {                                       // "Suggested package.json Dependencies"
      "layer": "CMS",                       // must exist in the layers table
      "npm_package": "payload",
      "suggested_version": "^3.0.0",        // optional
      "description": "...",                 // optional
      "evidence_confidence": "Medium",      // optional, free text
      "alternative_package": "strapi",      // optional
      "learn_url": "https://payloadcms.com" // optional
    }
  ],

  "design_tokens": [                        // optional, mirrors website.md's
    {                                       // "Visual Design System" table
      "category": "Typography",             // Typography | Colour | Layout | Other
      "property": "Primary font",
      "value": "Inter, sans-serif",
      "evidence": "...",
      "confidence": "High"                  // High | Medium | Low
    }
  ]
}
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "website_analysis.db"
VALID_CONFIDENCE = {"High", "Medium", "Low"}
VALID_DESIGN_CATEGORY = {"Typography", "Colour", "Layout", "Other"}


class ValidationError(Exception):
    pass


def load_run(json_path: Path) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_run(run: dict, valid_layers: set) -> None:
    if not run.get("site_url"):
        raise ValidationError("site_url is required")
    if not run.get("report_path"):
        raise ValidationError("report_path is required")

    for i, dep in enumerate(run.get("dependencies", [])):
        for field in ("layer", "technology", "evidence", "confidence"):
            if not dep.get(field):
                raise ValidationError(f"dependencies[{i}].{field} is required")
        if dep["layer"] not in valid_layers:
            raise ValidationError(
                f"dependencies[{i}].layer {dep['layer']!r} is not in the layers table. "
                f"Valid layers: {sorted(valid_layers)}"
            )
        if dep["confidence"] not in VALID_CONFIDENCE:
            raise ValidationError(
                f"dependencies[{i}].confidence {dep['confidence']!r} must be one of {VALID_CONFIDENCE}"
            )

    for i, u in enumerate(run.get("uncertainties", [])):
        if not u.get("question"):
            raise ValidationError(f"uncertainties[{i}].question is required")

    for i, jd in enumerate(run.get("js_dependencies", [])):
        for field in ("layer", "npm_package"):
            if not jd.get(field):
                raise ValidationError(f"js_dependencies[{i}].{field} is required")
        if jd["layer"] not in valid_layers:
            raise ValidationError(
                f"js_dependencies[{i}].layer {jd['layer']!r} is not in the layers table. "
                f"Valid layers: {sorted(valid_layers)}"
            )

    for i, dt in enumerate(run.get("design_tokens", [])):
        for field in ("category", "property", "value", "evidence", "confidence"):
            if not dt.get(field):
                raise ValidationError(f"design_tokens[{i}].{field} is required")
        if dt["category"] not in VALID_DESIGN_CATEGORY:
            raise ValidationError(
                f"design_tokens[{i}].category {dt['category']!r} must be one of {VALID_DESIGN_CATEGORY}"
            )
        if dt["confidence"] not in VALID_CONFIDENCE:
            raise ValidationError(
                f"design_tokens[{i}].confidence {dt['confidence']!r} must be one of {VALID_CONFIDENCE}"
            )


def get_or_create_site(conn: sqlite3.Connection, url: str) -> int:
    row = conn.execute("SELECT id FROM sites WHERE url = ?", (url,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute("INSERT INTO sites (url) VALUES (?)", (url,))
    return cur.lastrowid


def log_run(json_path: Path, db_path: Path = DB_PATH) -> None:
    run = load_run(json_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        valid_layers = {r[0] for r in conn.execute("SELECT name FROM layers")}
        validate_run(run, valid_layers)

        conn.execute("BEGIN")
        site_id = get_or_create_site(conn, run["site_url"])

        run_fields = {
            "site_id": site_id,
            "pages_examined": run.get("pages_examined"),
            "limitations": run.get("limitations"),
            "overview": run.get("overview"),
            "report_path": run["report_path"],
        }
        if run.get("access_date"):
            run_fields["access_date"] = run["access_date"]

        columns = ", ".join(run_fields.keys())
        placeholders = ", ".join("?" for _ in run_fields)
        cur = conn.execute(
            f"INSERT INTO analysis_runs ({columns}) VALUES ({placeholders})",
            tuple(run_fields.values()),
        )
        run_id = cur.lastrowid

        for dep in run.get("dependencies", []):
            conn.execute(
                "INSERT INTO dependencies (run_id, layer, technology, version, evidence, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, dep["layer"], dep["technology"], dep.get("version"), dep["evidence"], dep["confidence"]),
            )

        for u in run.get("uncertainties", []):
            conn.execute(
                "INSERT INTO uncertainties (run_id, question, evidence_needed) VALUES (?, ?, ?)",
                (run_id, u["question"], u.get("evidence_needed")),
            )

        for jd in run.get("js_dependencies", []):
            conn.execute(
                "INSERT INTO js_dependencies "
                "(run_id, layer, npm_package, suggested_version, description, evidence_confidence, "
                "alternative_package, learn_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    jd["layer"],
                    jd["npm_package"],
                    jd.get("suggested_version"),
                    jd.get("description"),
                    jd.get("evidence_confidence"),
                    jd.get("alternative_package"),
                    jd.get("learn_url"),
                ),
            )

        for dt in run.get("design_tokens", []):
            conn.execute(
                "INSERT INTO design_tokens (run_id, category, property, value, evidence, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, dt["category"], dt["property"], dt["value"], dt["evidence"], dt["confidence"]),
            )

        conn.commit()

        n_deps = len(run.get("dependencies", []))
        n_unc = len(run.get("uncertainties", []))
        n_js = len(run.get("js_dependencies", []))
        n_design = len(run.get("design_tokens", []))
        print(f"Logged run {run_id} for site {run['site_url']} (site id {site_id})")
        print(f"  dependencies: {n_deps}, uncertainties: {n_unc}, js_dependencies: {n_js}, design_tokens: {n_design}")
        print(f"  report_path: {run['report_path']}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python log_run.py <run.json>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        log_run(path)
    except (ValidationError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
