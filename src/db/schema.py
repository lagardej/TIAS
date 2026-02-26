"""
schema.py — SQLite schema definitions for TIAS V2.

Two databases:
  campaigns/{faction}/{date}/savegame.db  — gamestate snapshot (populated by stage)
  campaigns/{faction}/campaign.db         — session data (dialogue_fts, decision_log)

Versioned by domain group:
  V1: earth, space, intel, research (current)
  V2: fleet combat, alien presence, war state (future — when late-game data available)
"""

# ---------------------------------------------------------------------------
# savegame.db — snapshot tables
# ---------------------------------------------------------------------------

SAVEGAME_SCHEMA = """

-- Metadata
CREATE TABLE IF NOT EXISTS meta (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
-- keys: schema_version, iso_date, faction_slug, faction_display, faction_key, generated_at

-- ---------------------------------------------------------------------------
-- V1: EARTH DOMAIN
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gs_global (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),  -- enforces single row
    co2_ppm             REAL,
    sea_level_anomaly   REAL,
    nuclear_strikes     INTEGER,
    loose_nukes         INTEGER
);

CREATE TABLE IF NOT EXISTS gs_nations (
    nation_key          INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    gdp_t               REAL,       -- trillions USD
    gdp_delta_pct       REAL,
    unrest              REAL,
    unrest_delta        REAL,
    democracy           REAL,
    nukes               INTEGER
);

CREATE TABLE IF NOT EXISTS gs_control_points (
    cp_key              INTEGER PRIMARY KEY,
    nation_key          INTEGER NOT NULL,
    faction_key         INTEGER NOT NULL,
    faction_name        TEXT NOT NULL,
    cp_type             TEXT NOT NULL,  -- Executive, Legislature, MassMedia, etc.
    is_player           INTEGER NOT NULL DEFAULT 0,  -- 1 if player faction
    FOREIGN KEY (nation_key) REFERENCES gs_nations(nation_key)
);
CREATE INDEX IF NOT EXISTS idx_cp_nation ON gs_control_points(nation_key);
CREATE INDEX IF NOT EXISTS idx_cp_faction ON gs_control_points(faction_key);
CREATE INDEX IF NOT EXISTS idx_cp_type ON gs_control_points(cp_type);

CREATE TABLE IF NOT EXISTS gs_public_opinion (
    nation_key          INTEGER NOT NULL,
    nation_name         TEXT NOT NULL,
    faction_slug        TEXT NOT NULL,  -- resist, destroy, exploit, etc.
    faction_name        TEXT NOT NULL,
    pct                 REAL,
    delta_pp            REAL,
    PRIMARY KEY (nation_key, faction_slug),
    FOREIGN KEY (nation_key) REFERENCES gs_nations(nation_key)
);

CREATE TABLE IF NOT EXISTS gs_federations (
    fed_key             INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    member_count        INTEGER,
    major_power_count   INTEGER
);

CREATE TABLE IF NOT EXISTS gs_faction_resources (
    faction_key         INTEGER PRIMARY KEY,
    faction_name        TEXT NOT NULL,
    is_player           INTEGER NOT NULL DEFAULT 0,
    money               INTEGER,
    influence           INTEGER,
    ops                 INTEGER,
    boost               REAL,
    mc_cap              INTEGER
);

-- ---------------------------------------------------------------------------
-- V1: INTEL DOMAIN
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gs_councilors_enemy (
    councilor_key       INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    councilor_type      TEXT,
    faction_key         INTEGER,
    faction_name        TEXT,
    intel_level         REAL,
    suspicion           REAL,
    location            TEXT
);

CREATE TABLE IF NOT EXISTS gs_councilors_player (
    councilor_key       INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    councilor_type      TEXT,
    location            TEXT
);

CREATE TABLE IF NOT EXISTS gs_faction_intel (
    faction_key         INTEGER PRIMARY KEY,
    faction_name        TEXT NOT NULL,
    is_player           INTEGER NOT NULL DEFAULT 0,
    intel_level         REAL
);

-- ---------------------------------------------------------------------------
-- V1: RESEARCH DOMAIN
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gs_research_completed (
    tech_name           TEXT PRIMARY KEY
);

-- ---------------------------------------------------------------------------
-- V1: SPACE DOMAIN
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gs_habs (
    hab_key             INTEGER PRIMARY KEY,
    parent_body_key     INTEGER,        -- TISpaceBodyState key
    parent_body_name    TEXT,           -- denormalised display name for convenience
    name                TEXT NOT NULL,
    hab_type            TEXT NOT NULL,  -- Base, Station
    tier                INTEGER,
    faction_key         INTEGER,
    faction_name        TEXT,
    is_player           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_habs_body ON gs_habs(parent_body_key);
CREATE INDEX IF NOT EXISTS idx_habs_faction ON gs_habs(faction_key);

CREATE TABLE IF NOT EXISTS gs_hab_modules (
    module_key          INTEGER PRIMARY KEY,  -- TIHabModuleState key
    hab_key             INTEGER NOT NULL,     -- FK -> gs_habs
    module_name         TEXT NOT NULL,        -- TIHabModuleTemplate dataName
    display_name        TEXT,                 -- localized display name
    tier                INTEGER,              -- from TIHabModuleTemplate
    crew                INTEGER,              -- from TIHabModuleTemplate (positive = requires crew)
    power               INTEGER,              -- from TIHabModuleTemplate (negative = consuming, positive = generating)
    construction_completed  INTEGER NOT NULL DEFAULT 1,  -- 0 if still building
    completion_date     TEXT,                 -- ISO date: ETA if building, actual if complete
    powered             INTEGER NOT NULL DEFAULT 1,
    destroyed           INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (hab_key) REFERENCES gs_habs(hab_key)
);
CREATE INDEX IF NOT EXISTS idx_hab_modules_hab ON gs_hab_modules(hab_key);
CREATE INDEX IF NOT EXISTS idx_hab_modules_name ON gs_hab_modules(module_name);

CREATE TABLE IF NOT EXISTS gs_space_bodies (
    body_key            INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    object_type         TEXT,           -- Star, Planet, Moon, Asteroid, DwarfPlanet, etc.
    barycenter_key      INTEGER,        -- parent body key (null for Sol)
    max_hab_tier        INTEGER,
    has_hab_sites       INTEGER NOT NULL DEFAULT 0,  -- 1 if habSites non-empty
    next_window_date    TEXT,           -- null if no launch window data
    days_away           INTEGER,
    penalty_pct         REAL
);
CREATE INDEX IF NOT EXISTS idx_bodies_barycenter ON gs_space_bodies(barycenter_key);
CREATE INDEX IF NOT EXISTS idx_bodies_type ON gs_space_bodies(object_type);

CREATE TABLE IF NOT EXISTS gs_fleets (
    fleet_key           INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    faction_key         INTEGER,
    faction_name        TEXT,
    body_key            INTEGER,        -- barycenter body key
    location            TEXT,           -- human-readable e.g. 'orbiting Sol'
    is_player           INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (body_key) REFERENCES gs_space_bodies(body_key)
);
CREATE INDEX IF NOT EXISTS idx_fleets_body ON gs_fleets(body_key);

"""

# ---------------------------------------------------------------------------
# campaign.db — cross-date session tables
# ---------------------------------------------------------------------------

CAMPAIGN_SCHEMA = """

CREATE TABLE IF NOT EXISTS dialogue_fts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    iso_date    TEXT NOT NULL,
    turn        INTEGER NOT NULL,
    speaker     TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fts_session ON dialogue_fts(session_id);
CREATE INDEX IF NOT EXISTS idx_fts_date ON dialogue_fts(iso_date);

CREATE TABLE IF NOT EXISTS decision_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action_key  TEXT NOT NULL,     -- normalised action string
    decision    TEXT NOT NULL,     -- 'allowed' | 'denied'
    iso_date    TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_decision_key ON decision_log(action_key);

"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"


def init_savegame_db(conn) -> None:
    """Create all savegame snapshot tables. Safe to call on existing DB."""
    conn.executescript(SAVEGAME_SCHEMA)
    conn.execute(
        "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)",
        (SCHEMA_VERSION,)
    )
    conn.commit()


def init_campaign_db(conn) -> None:
    """Create campaign session tables. Safe to call on existing DB."""
    conn.executescript(CAMPAIGN_SCHEMA)
    conn.commit()
