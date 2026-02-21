"""
query.py — Read gamestate from savegame.db for CODEX report generation.

Produces the same structured text output as the old gamestate_*.txt files,
but sourced from SQL queries against the normalized savegame.db schema.

Public API:
    build_codex_report(savegame_db: Path) -> str
"""

import sqlite3
from pathlib import Path


def _conn(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Earth domain
# ---------------------------------------------------------------------------

def _section_global(conn) -> list[str]:
    row = conn.execute(
        "SELECT co2_ppm, sea_level_anomaly, nuclear_strikes, loose_nukes FROM gs_global"
    ).fetchone()
    if not row:
        return []
    return [
        "## Global",
        f"CO2: {row['co2_ppm']:.1f} ppm  |  Sea level anomaly: {row['sea_level_anomaly']:.1f} cm",
        f"Nuclear strikes: {row['nuclear_strikes']}  |  Loose nukes: {row['loose_nukes']}",
        "",
    ]


def _section_nations(conn) -> list[str]:
    rows = conn.execute("""
        SELECT n.name, n.gdp_t, n.gdp_delta_pct, n.unrest, n.unrest_delta,
               n.democracy, n.nukes, n.nation_key
        FROM gs_nations n
        WHERE n.gdp_t > 0.1          -- major nations only (>100B)
        ORDER BY n.gdp_t DESC
        LIMIT 30
    """).fetchall()
    if not rows:
        return []

    # Build CP summary per nation: {nation_key: {faction_name: count}}
    cp_rows = conn.execute(
        "SELECT nation_key, faction_name FROM gs_control_points"
    ).fetchall()
    cp_map: dict[int, dict[str, int]] = {}
    for cp in cp_rows:
        nk = cp['nation_key']
        fn = cp['faction_name']
        cp_map.setdefault(nk, {})
        cp_map[nk][fn] = cp_map[nk].get(fn, 0) + 1

    lines = ["## Nations", "Nation,GDP,ΔGDP,Unrest,ΔUnrest,Demo,Nukes,Control Points"]
    for r in rows:
        nk = r['nation_key']
        cp_summary = cp_map.get(nk, {})
        cp_str = ' '.join(f"{f}:{c}" for f, c in sorted(cp_summary.items()))
        gdp_d  = f"{r['gdp_delta_pct']:+.1f}%" if r['gdp_delta_pct'] else '0%'
        un_d   = f"{r['unrest_delta']:+.2f}" if r['unrest_delta'] else '0'
        lines.append(
            f"{r['name']},{r['gdp_t']:.2f}T,{gdp_d},"
            f"{r['unrest']:.2f},{un_d},{r['democracy']:.1f},"
            f"{r['nukes']},{cp_str}"
        )
    lines.append("")
    return lines


def _section_public_opinion(conn) -> list[str]:
    """Public opinion for player-controlled nations (has at least one player CP)."""
    player_nation_keys = {
        row[0] for row in conn.execute(
            "SELECT DISTINCT nation_key FROM gs_control_points WHERE is_player = 1"
        ).fetchall()
    }
    if not player_nation_keys:
        return []

    lines = ["## Public Opinion (Player Nations)"]
    lines.append("Nation,Resist,ΔResist,Destroy,ΔDestroy,Exploit,ΔExploit,Undecided")

    for nk in sorted(player_nation_keys):
        nation_name = conn.execute(
            "SELECT name FROM gs_nations WHERE nation_key = ?", (nk,)
        ).fetchone()
        if not nation_name:
            continue
        rows = conn.execute("""
            SELECT faction_slug, pct, delta_pp
            FROM gs_public_opinion
            WHERE nation_key = ?
        """, (nk,)).fetchall()
        po = {r['faction_slug']: (r['pct'], r['delta_pp']) for r in rows}

        def fmt(slug):
            pct, delta = po.get(slug, (0, 0))
            return f"{pct:.0f}%,{delta:+.1f}pp"

        lines.append(
            f"{nation_name['name']},"
            f"{fmt('resist')},{fmt('destroy')},{fmt('exploit')},"
            f"{po.get('undecided', (0,0))[0]:.0f}%"
        )
    lines.append("")
    return lines


def _section_federations(conn) -> list[str]:
    rows = conn.execute(
        "SELECT name, member_count, major_power_count FROM gs_federations ORDER BY member_count DESC"
    ).fetchall()
    if not rows:
        return []
    lines = ["## Federations"]
    for r in rows:
        lines.append(f"{r['name']}: {r['member_count']} members ({r['major_power_count']} major powers)")
    lines.append("")
    return lines


def _section_faction_resources(conn) -> list[str]:
    rows = conn.execute("""
        SELECT faction_name, is_player, money, influence, ops, boost, mc_cap
        FROM gs_faction_resources
        ORDER BY is_player DESC, money DESC
    """).fetchall()
    if not rows:
        return []
    lines = [
        "## Faction Resources",
        f"  {'Faction':<22} {'Money':>10}  {'Influence':>9}  {'Ops':>6}  {'Boost':>6}  {'MC':>6}",
        "  " + "-" * 68,
    ]
    for r in rows:
        mark = " *" if r['is_player'] else ""
        lines.append(
            f"  {r['faction_name']:<22}{mark} "
            f"{r['money']:>12,.0f}  "
            f"{r['influence']:>9.0f}  "
            f"{r['ops']:>6.0f}  "
            f"{r['boost']:>6.1f}  "
            f"{r['mc_cap']:>6.0f}"
        )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Intel domain
# ---------------------------------------------------------------------------

def _section_enemy_councilors(conn) -> list[str]:
    rows = conn.execute("""
        SELECT name, councilor_type, faction_name, intel_level, suspicion, location
        FROM gs_councilors_enemy
        ORDER BY faction_name, name
    """).fetchall()
    if not rows:
        return []
    lines = [
        "## Known Enemy Councilors",
        f"  {'Name':<25} {'Type':<16} {'Faction':<22} {'Intel':>6}  {'Susp':>6}  Location",
        "  " + "-" * 100,
    ]
    for r in rows:
        sus = f"{r['suspicion']:.1f}" if r['suspicion'] else '-'
        lines.append(
            f"  {r['name']:<25} {r['councilor_type']:<16} {r['faction_name']:<22} "
            f"{r['intel_level']:>6.2f}  {sus:>6}  {r['location']}"
        )
    lines.append("")
    return lines


def _section_player_councilors(conn) -> list[str]:
    rows = conn.execute(
        "SELECT name, councilor_type, location FROM gs_councilors_player ORDER BY name"
    ).fetchall()
    if not rows:
        return []
    lines = [
        "## Our Councilors",
        f"  {'Name':<25} {'Type':<16} Location",
        "  " + "-" * 70,
    ]
    for r in rows:
        lines.append(f"  {r['name']:<25} {r['councilor_type']:<16} {r['location']}")
    lines.append("")
    return lines


def _section_faction_intel(conn) -> list[str]:
    rows = conn.execute("""
        SELECT faction_name, intel_level, is_player
        FROM gs_faction_intel
        ORDER BY intel_level DESC
    """).fetchall()
    if not rows:
        return []
    lines = ["## Faction Intel Levels"]
    for r in rows:
        mark = " *" if r['is_player'] else ""
        lines.append(f"  {r['faction_name']:<22}{mark}  {r['intel_level']:.2f}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Research domain
# ---------------------------------------------------------------------------

def _section_research(conn) -> list[str]:
    rows = conn.execute(
        "SELECT tech_name FROM gs_research_completed ORDER BY tech_name"
    ).fetchall()
    if not rows:
        return []
    lines = [f"## Completed Technologies ({len(rows)} total)"]
    for r in rows:
        lines.append(f"  {r['tech_name']}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Space domain
# ---------------------------------------------------------------------------

def _section_habs(conn) -> list[str]:
    rows = conn.execute("""
        SELECT COALESCE(sb.name, h.parent_body_name, '?') AS body,
               h.name, h.hab_type, h.tier, h.faction_name, h.is_player
        FROM gs_habs h
        LEFT JOIN gs_space_bodies sb ON sb.body_key = h.parent_body_key
        ORDER BY body, h.name
    """).fetchall()
    if not rows:
        return []

    by_body: dict[str, list] = {}
    for r in rows:
        body = r['body'] or '?'
        by_body.setdefault(body, []).append(r)

    lines = ["## Habs & Stations"]
    for body in sorted(by_body.keys()):
        lines.append(f"\n### {body}")
        lines.append(f"  {'Name':<30} {'Type':<10} {'Tier':<5} Faction")
        lines.append("  " + "-" * 65)
        for r in by_body[body]:
            mark = " *" if r['is_player'] else ""
            lines.append(
                f"  {r['name']:<30} {r['hab_type']:<10} T{r['tier']}    "
                f"{r['faction_name']}{mark}"
            )
    lines.append("")
    return lines


def _section_fleets(conn) -> list[str]:
    rows = conn.execute("""
        SELECT f.name, f.faction_name, f.location, f.is_player
        FROM gs_fleets f
        ORDER BY f.name
    """).fetchall()
    if not rows:
        return []
    lines = [
        "## Fleets",
        f"  {'Name':<25} {'Faction':<20} Location",
        "  " + "-" * 65,
    ]
    for r in rows:
        mark = " *" if r['is_player'] else ""
        lines.append(f"  {r['name']:<25} {r['faction_name']:<20} {r['location']}{mark}")
    lines.append("")
    return lines


def _section_launch_windows(conn) -> list[str]:
    """Bodies with launch window data."""
    rows = conn.execute(
        "SELECT name, next_window_date, days_away, penalty_pct "
        "FROM gs_space_bodies WHERE next_window_date IS NOT NULL ORDER BY days_away"
    ).fetchall()
    if not rows:
        return []
    lines = ["## Launch Windows"]
    for r in rows:
        penalty = f", penalty {r['penalty_pct']:.0f}%" if r['penalty_pct'] else ""
        lines.append(
            f"  {r['name']}: next window {r['next_window_date']} "
            f"({r['days_away']} days){penalty}"
        )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_codex_report(savegame_db: Path) -> str:
    """
    Build the full CODEX gamestate report from savegame.db.
    Returns a multi-section text string, same format as old gamestate_*.txt files.
    """
    conn = _conn(savegame_db)
    try:
        sections = [
            "# EARTH & POLITICAL STATE", "",
            *_section_global(conn),
            *_section_nations(conn),
            *_section_public_opinion(conn),
            *_section_federations(conn),
            *_section_faction_resources(conn),
            "# INTELLIGENCE STATE", "",
            *_section_enemy_councilors(conn),
            *_section_player_councilors(conn),
            *_section_faction_intel(conn),
            "# RESEARCH STATE", "",
            *_section_research(conn),
            "# SPACE STATE", "",
            *_section_habs(conn),
            *_section_fleets(conn),
            *_section_launch_windows(conn),
        ]
        return "\n".join(sections).strip()
    finally:
        conn.close()
