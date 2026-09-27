-- Schema for logging website stack/dependency analysis results
-- (used alongside prompt.md's Analysis Process and Required Output)
--
-- NOTE: SQLite does not enforce FOREIGN KEY / ON DELETE CASCADE unless the
-- connection runs `PRAGMA foreign_keys = ON;` first. Any script that opens
-- this database must set that pragma before writing or deleting.

CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    access_date TEXT NOT NULL DEFAULT (datetime('now')),
    pages_examined TEXT,
    limitations TEXT,
    overview TEXT,
    report_path TEXT NOT NULL       -- path to the human-readable report, e.g. website/example.com/analysis.md
);

-- Fixed vocabulary for `dependencies.layer`, taken from the layer list in
-- prompt.md's Required Output section. Keeps cross-site queries consistent
-- (e.g. "Frontend framework" vs "frontend"). Add a new row here first if a
-- genuinely new layer type is needed — never invent one inline in an insert.
CREATE TABLE IF NOT EXISTS layers (
    name TEXT PRIMARY KEY
);

INSERT OR IGNORE INTO layers (name) VALUES
    ('Language'),
    ('Frontend framework'),
    ('Rendering approach'),
    ('Router'),
    ('Styling'),
    ('UI/component library'),
    ('State management'),
    ('Data fetching'),
    ('Build tooling'),
    ('Backend/runtime'),
    ('API framework'),
    ('CMS'),
    ('Database'),
    ('Authentication'),
    ('Analytics'),
    ('Testing'),
    ('Hosting'),
    ('Deployment');

CREATE TABLE IF NOT EXISTS dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    layer TEXT NOT NULL REFERENCES layers(name),
    technology TEXT NOT NULL,       -- e.g. React, Vite, Node.js, Shopify (free text: package space is open-ended)
    version TEXT,                   -- exact version if verifiable, else NULL
    evidence TEXT NOT NULL,         -- what was observed and where
    confidence TEXT NOT NULL CHECK (confidence IN ('High', 'Medium', 'Low'))
);

CREATE TABLE IF NOT EXISTS uncertainties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    evidence_needed TEXT
);

-- Mirrors website.md's "Suggested package.json Dependencies" table. These are
-- recommendations for recreating the stack, never confirmed facts about the
-- real site's package.json.
CREATE TABLE IF NOT EXISTS js_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    layer TEXT NOT NULL REFERENCES layers(name),
    npm_package TEXT NOT NULL,
    suggested_version TEXT,
    description TEXT,
    evidence_confidence TEXT,
    alternative_package TEXT,
    learn_url TEXT
);

-- Mirrors website.md's "Visual Design System" table: fonts, colours, layout
-- rules extracted from public CSS/HTML. Never used to store or reproduce
-- copyrighted logos/illustrations/imagery — system-level design tokens only.
CREATE TABLE IF NOT EXISTS design_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN ('Typography', 'Colour', 'Layout', 'Other')),
    property TEXT NOT NULL,         -- e.g. "Primary font", "Primary colour", "Container max-width", "Border radius"
    value TEXT NOT NULL,            -- e.g. "Inter, sans-serif", "#0F62FE", "1280px", "8px"
    evidence TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('High', 'Medium', 'Low'))
);

CREATE INDEX IF NOT EXISTS idx_runs_site ON analysis_runs(site_id);
CREATE INDEX IF NOT EXISTS idx_deps_run ON dependencies(run_id);
CREATE INDEX IF NOT EXISTS idx_uncert_run ON uncertainties(run_id);
CREATE INDEX IF NOT EXISTS idx_jsdeps_run ON js_dependencies(run_id);
CREATE INDEX IF NOT EXISTS idx_design_run ON design_tokens(run_id);
