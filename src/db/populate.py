"""
populate.py — Populate savegame.db from the raw savegame SQLite DB.

Reuses extractor logic from preset/extractors/ to avoid duplication.
Called by stage/command.py after parse phase.

Usage:
    from src.db.populate import populate_savegame_db
    populate_savegame_db(savegame_db, output_db, faction_slug, iso_date, helpers)
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.db.schema import init_savegame_db, SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def populate_savegame_db(
    raw_db: Path,
    output_db: Path,
    faction_slug: str,
    iso_date: str,
    helpers: dict,
    game_date=None,
    templates_file: Path = None,
) -> None:
    """
    Populate savegame.db from the raw parse DB.

    Args:
        raw_db:          Path to build/savegame_{date}.db (raw JSON blobs)
        output_db:       Path to campaigns/{faction}/{date}/savegame.db
        faction_slug:    e.g. 'resist'
        iso_date:        e.g. '2027-08-01'
        helpers:         Shared helper functions from preset/command.py
        game_date:       datetime.date for launch window calculations
        templates_file:  Path to TISpaceBodyTemplate.json
    """
    _load_gs         = helpers['load_gs']
    _player_faction  = helpers['player_faction']
    _faction_name_map = helpers['faction_name_map']
    _nation_map      = helpers['nation_map']
    _hab_body_map    = helpers['hab_body_map']

    player_faction_key, pf = _player_faction(raw_db)
    faction_names          = _faction_name_map(raw_db)
    nation_map_data        = _nation_map(raw_db)
    player_faction_display = faction_names.get(player_faction_key, faction_slug)

    conn = sqlite3.connect(output_db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        init_savegame_db(conn)
        _clear_snapshot(conn)

        _insert_meta(conn, faction_slug, faction_key=player_faction_key,
                     faction_display=player_faction_display, iso_date=iso_date)
        _populate_earth(conn, raw_db, _load_gs, _player_faction,
                        _faction_name_map, _nation_map,
                        player_faction_key, faction_names, nation_map_data, pf)
        _populate_intel(conn, raw_db, _load_gs, _player_faction,
                        _faction_name_map, _nation_map,
                        player_faction_key, faction_names, nation_map_data, pf)
        _populate_research(conn, raw_db, _load_gs)
        _populate_space(conn, raw_db, _load_gs, _player_faction,
                        _faction_name_map, _hab_body_map,
                        player_faction_key, faction_names,
                        game_date=game_date, templates_file=templates_file)
        conn.commit()
        logging.info(f"savegame.db populated: {output_db}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_snapshot(conn: sqlite3.Connection) -> None:
    """Wipe all snapshot tables for a fresh insert."""
    tables = [
        "gs_global", "gs_nations", "gs_control_points", "gs_public_opinion",
        "gs_federations", "gs_faction_resources",
        "gs_councilors_enemy", "gs_councilors_player", "gs_faction_intel",
        "gs_research_completed",
        "gs_habs", "gs_fleets", "gs_launch_windows",
    ]
    for t in tables:
        conn.execute(f"DELETE FROM {t}")


def _insert_meta(conn, faction_slug, faction_key, faction_display, iso_date):
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        ("schema_version",   SCHEMA_VERSION),
        ("iso_date",         iso_date),
        ("faction_slug",     faction_slug),
        ("faction_display",  faction_display),
        ("faction_key",      str(faction_key)),
        ("generated_at",     now),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", rows
    )


# ---------------------------------------------------------------------------
# Earth domain
# ---------------------------------------------------------------------------

def _populate_earth(conn, raw_db, _load_gs, _player_faction,
                    _faction_name_map, _nation_map,
                    player_faction_key, faction_names, nation_map_data, pf):

    # --- Global ---
    gvs_list = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIGlobalValuesState')
    gvs = gvs_list[0]['Value'] if gvs_list else {}
    conn.execute(
        "INSERT OR REPLACE INTO gs_global(id, co2_ppm, sea_level_anomaly, nuclear_strikes, loose_nukes) "
        "VALUES (1, ?, ?, ?, ?)",
        (
            gvs.get('earthAtmosphericCO2_ppm'),
            gvs.get('globalSeaLevelAnomaly_cm'),
            gvs.get('nuclearStrikes', 0),
            gvs.get('looseNukes', 0),
        )
    )

    # --- Nations ---
    # Insert ALL non-alien nations (major filter is for display only, not DB)
    major_nations = [(nk, n) for nk, n in nation_map_data.items() if n.get('capital')]
    gdp_hist_cache = {}
    unrest_hist_cache = {}
    for nk, n in major_nations:
        gdp_hist   = n.get('historyGDP', [])
        unrest_hist = n.get('historyUnrest', [])
        gdp_delta   = ((gdp_hist[-1] - gdp_hist[-6]) / gdp_hist[-6] * 100) \
                      if len(gdp_hist) >= 6 and gdp_hist[-6] > 0 else 0.0
        unrest_delta = (unrest_hist[-1] - unrest_hist[-6]) \
                       if len(unrest_hist) >= 6 else 0.0
        gdp_hist_cache[nk]    = gdp_delta
        unrest_hist_cache[nk] = unrest_delta
        conn.execute(
            "INSERT OR REPLACE INTO gs_nations "
            "(nation_key, name, gdp_t, gdp_delta_pct, unrest, unrest_delta, democracy, nukes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                nk,
                n.get('displayName', '?'),
                n.get('GDP', 0) / 1e12,
                gdp_delta,
                n.get('unrest', 0),
                unrest_delta,
                n.get('democracy', 0),
                n.get('numNuclearWeapons', 0),
            )
        )

    # --- Control points ---
    all_cps = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIControlPoint')
    for cp in all_cps:
        v   = cp['Value']
        cpk = cp['Key']['value']
        nk  = (v.get('nation') or {}).get('value')
        fk  = (v.get('faction') or {}).get('value')
        if nk is None:
            continue
        fname    = faction_names.get(fk, 'Uncontrolled') if fk else 'Uncontrolled'
        is_player = 1 if fk == player_faction_key else 0
        cp_type  = v.get('controlPointType', 'Unknown')
        # Skip CPs whose nation wasn't inserted (alien nations, etc.)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO gs_control_points "
                "(cp_key, nation_key, faction_key, faction_name, cp_type, is_player) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (cpk, nk, fk or -1, fname, cp_type, is_player)
            )
        except sqlite3.IntegrityError:
            logging.debug(f"Skipped CP {cpk}: nation_key {nk} not in gs_nations")

    # --- Public opinion (player nations only) ---
    # Public opinion keys = faction ideologyName capitalised (game constant, never changes)
    ideology_display: dict[str, str] = {
        'Resist':    'The Resistance',
        'Destroy':   'Humanity First',
        'Exploit':   'The Initiative',
        'Submit':    'The Servants',
        'Appease':   'The Protectorate',
        'Cooperate': 'The Academy',
        'Escape':    'Project Exodus',
        'Undecided': 'Undecided',
    }

    for nk in nation_map_data:
        n = nation_map_data.get(nk, {})
        if not n.get('capital') or not n.get('publicOpinion'):
            continue
        po      = n.get('publicOpinion', {})
        po_hist = n.get('historyPublicOpinion', [])
        po_old  = po_hist[-6] if len(po_hist) >= 6 else {}
        nation_name = n.get('displayName', '?')
        for raw_key, display in ideology_display.items():
            pct   = po.get(raw_key, 0)
            delta = (pct - po_old.get(raw_key, 0)) * 100
            conn.execute(
                "INSERT OR REPLACE INTO gs_public_opinion "
                "(nation_key, nation_name, faction_slug, faction_name, pct, delta_pp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (nk, nation_name, raw_key.lower(), display, pct * 100, delta)
            )

    # --- Federations ---
    feds = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIFederationState')
    for fed in feds:
        v = fed['Value']
        if not v.get('exists'):
            continue
        members = v.get('members', [])
        major   = sum(
            1 for m in members
            if nation_map_data.get(m['value'], {}).get('GDP', 0) > 1e12
            and not nation_map_data.get(m['value'], {}).get('aggregateNation')
        )
        conn.execute(
            "INSERT OR REPLACE INTO gs_federations(fed_key, name, member_count, major_power_count) "
            "VALUES (?, ?, ?, ?)",
            (fed['Key']['value'], v.get('displayNameWithArticle') or v.get('displayName', '?'),
             len(members), major)
        )

    # --- Faction resources ---
    factions = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIFactionState')
    for f in factions:
        v = f['Value']
        if not v.get('exists') or v.get('archived'):
            continue
        fk    = f['Key']['value']
        res   = v.get('resources', {})
        mc    = v.get('baseIncomes_year', {}).get('MissionControl', 0)
        conn.execute(
            "INSERT OR REPLACE INTO gs_faction_resources "
            "(faction_key, faction_name, is_player, money, influence, ops, boost, mc_cap) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fk,
                v.get('displayName', '?'),
                1 if fk == player_faction_key else 0,
                res.get('Money', 0),
                res.get('Influence', 0),
                res.get('Operations', 0),
                res.get('Boost', 0),
                mc,
            )
        )


# ---------------------------------------------------------------------------
# Intel domain
# ---------------------------------------------------------------------------

def _build_location_resolver(raw_db, _load_gs, nation_map_data):
    """Return a callable: location_dict → human-readable string."""
    regions      = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIRegionState')
    region_map   = {r['Key']['value']: r['Value'] for r in regions}
    region_nation = {}
    for nk, n in nation_map_data.items():
        for rk in (r.get('value') for r in n.get('regions', [])):
            region_nation[rk] = nk

    def resolve(loc: dict) -> str:
        if not loc:
            return 'unknown'
        loc_type = loc.get('$type', '')
        loc_key  = loc.get('value')
        if 'Region' in loc_type:
            region      = region_map.get(loc_key, {})
            nation_key  = region_nation.get(loc_key)
            nation      = nation_map_data.get(nation_key, {})
            region_name = region.get('displayName', f'region {loc_key}')
            nation_name = nation.get('displayName', '')
            return f"{region_name}, {nation_name}" if nation_name else region_name
        elif 'Hab' in loc_type:
            return f'hab {loc_key}'
        return f'unknown ({loc_key})'

    return resolve


def _populate_intel(conn, raw_db, _load_gs, _player_faction,
                    _faction_name_map, _nation_map,
                    player_faction_key, faction_names, nation_map_data, pf):

    councilors    = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TICouncilorState')
    councilor_map = {c['Key']['value']: c['Value'] for c in councilors}
    factions      = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIFactionState')
    resolve_loc   = _build_location_resolver(raw_db, _load_gs, nation_map_data)

    # Suspicion map
    suspicion_map: dict[int, float] = {}
    for f in factions:
        for entry in f['Value'].get('internalCouncilorSuspicion', []):
            ck  = entry['Key']['value']
            sus = entry['Value']
            suspicion_map[ck] = max(suspicion_map.get(ck, 0.0), sus)

    intel_entries = pf.get('intel', [])

    # Enemy councilors
    for entry in intel_entries:
        if 'TICouncilorState' not in entry['Key'].get('$type', ''):
            continue
        ck    = entry['Key']['value']
        level = entry['Value']
        c     = councilor_map.get(ck, {})
        if not c:
            continue
        fk = (c.get('faction') or {}).get('value')
        if fk == player_faction_key:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO gs_councilors_enemy "
            "(councilor_key, name, councilor_type, faction_key, faction_name, "
            "intel_level, suspicion, location) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ck,
                c.get('displayName', '?'),
                c.get('typeTemplateName', '?'),
                fk,
                faction_names.get(fk, '?'),
                level,
                suspicion_map.get(ck, 0.0),
                resolve_loc(c.get('location', {})),
            )
        )

    # Player councilors
    player_councilor_keys = {c['value'] for c in pf.get('councilors', [])}
    for ck in player_councilor_keys:
        c = councilor_map.get(ck, {})
        if not c:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO gs_councilors_player "
            "(councilor_key, name, councilor_type, location) "
            "VALUES (?, ?, ?, ?)",
            (
                ck,
                c.get('displayName', '?'),
                c.get('typeTemplateName', '?'),
                resolve_loc(c.get('location', {})),
            )
        )

    # Faction intel levels
    for entry in intel_entries:
        if 'TIFactionState' not in entry['Key'].get('$type', ''):
            continue
        fk    = entry['Key']['value']
        level = entry['Value']
        conn.execute(
            "INSERT OR REPLACE INTO gs_faction_intel "
            "(faction_key, faction_name, is_player, intel_level) "
            "VALUES (?, ?, ?, ?)",
            (fk, faction_names.get(fk, '?'), 1 if fk == player_faction_key else 0, level)
        )


# ---------------------------------------------------------------------------
# Research domain
# ---------------------------------------------------------------------------

def _populate_research(conn, raw_db, _load_gs):
    grs_list = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIGlobalResearchState')
    grs = grs_list[0]['Value'] if grs_list else {}
    for tech in grs.get('finishedTechsNames', []):
        conn.execute(
            "INSERT OR IGNORE INTO gs_research_completed(tech_name) VALUES (?)", (tech,)
        )


# ---------------------------------------------------------------------------
# Space domain
# ---------------------------------------------------------------------------

def _populate_space(conn, raw_db, _load_gs, _player_faction,
                    _faction_name_map, _hab_body_map,
                    player_faction_key, faction_names,
                    game_date=None, templates_file=None):

    hab_body  = _hab_body_map(raw_db)  # outposts: hab_key → body name via habSite
    habs      = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIHabState')
    fleets    = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TISpaceFleetState')
    bodies    = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TISpaceBodyState')
    body_name = {b['Key']['value']: b['Value'].get('displayName', '?') for b in bodies}

    # Build orbit → (body_key, body_name) map for stations
    orbits = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIOrbitState')
    orbit_body: dict[int, tuple[int | None, str]] = {}
    for o in orbits:
        pb  = (o['Value'].get('parentBody') or {})
        bk  = pb.get('value')
        orbit_body[o['Key']['value']] = (bk, body_name.get(bk, '?') if bk else '?')

    # Build habSite → (body_key, body_name) for outposts
    sites     = _load_gs(raw_db, 'PavonisInteractive.TerraInvicta.TIHabSiteState')
    site_body: dict[int, tuple[int | None, str]] = {}
    for s in sites:
        pb = (s['Value'].get('parentBody') or {})
        bk = pb.get('value')
        site_body[s['Key']['value']] = (bk, body_name.get(bk, '?') if bk else '?')

    # Habs
    for h in habs:
        v = h['Value']
        if not v.get('exists') or v.get('archived'):
            continue
        hk        = h['Key']['value']
        fk        = (v.get('faction') or {}).get('value')
        orbit_ref = (v.get('orbitState') or {}).get('value')
        site_ref  = (v.get('habSite') or {}).get('value')
        bary_ref  = (v.get('barycenter') or {}).get('value')
        if site_ref:
            pbk, pbn = site_body.get(site_ref, (None, '?'))
        elif bary_ref:
            pbk, pbn = bary_ref, body_name.get(bary_ref, '?')
        elif orbit_ref:
            pbk, pbn = orbit_body.get(orbit_ref, (None, '?'))
        else:
            pbk, pbn = None, '?'
        conn.execute(
            "INSERT OR REPLACE INTO gs_habs "
            "(hab_key, parent_body_key, parent_body_name, name, hab_type, tier, faction_key, faction_name, is_player) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hk, pbk, pbn,
                v.get('displayName', '?'),
                v.get('habType', '?'),
                v.get('tier', 0),
                fk,
                faction_names.get(fk, 'None') if fk else 'None',
                1 if fk == player_faction_key else 0,
            )
        )

    # Launch windows
    if game_date and templates_file:
        from src.preset.launch_windows import calculate_launch_windows
        windows = calculate_launch_windows(game_date, templates_file)
        for destination, data in windows.items():
            conn.execute(
                "INSERT OR REPLACE INTO gs_launch_windows "
                "(destination, next_window_date, days_away, penalty_pct) "
                "VALUES (?, ?, ?, ?)",
                (
                    destination,
                    data.get('next_window'),
                    data.get('days_away'),
                    data.get('current_penalty', 0),
                )
            )

    # Fleets
    for f in fleets:
        v = f['Value']
        if not v.get('exists') or v.get('archived') or v.get('dummyFleet'):
            continue
        fk  = (v.get('faction') or {}).get('value')
        bk  = (v.get('barycenter') or {}).get('value')
        location = f"orbiting {body_name.get(bk, str(bk))}" if bk else 'in transit'
        conn.execute(
            "INSERT OR REPLACE INTO gs_fleets "
            "(fleet_key, name, faction_key, faction_name, location, is_player) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                f['Key']['value'],
                v.get('displayName', '?'),
                fk,
                faction_names.get(fk, '?') if fk else '?',
                location,
                1 if fk == player_faction_key else 0,
            )
        )
