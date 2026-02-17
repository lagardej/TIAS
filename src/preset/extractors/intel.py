"""
Intel domain extractor: known enemy councilors, faction intel levels, our councilors.
"""

from pathlib import Path


def write_intel(db_path: Path, out: Path, helpers: dict):
    """Extract intelligence game state.
    
    Args:
        db_path: Path to savegame DB
        out: Output file path
        helpers: Dict of shared helper functions
    """
    _load_gs = helpers['load_gs']
    _player_faction = helpers['player_faction']
    _faction_name_map = helpers['faction_name_map']
    _nation_map = helpers['nation_map']
    
    faction_names      = _faction_name_map(db_path)
    player_faction_key, pf = _player_faction(db_path)
    factions           = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    councilors         = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TICouncilorState')
    councilor_map      = {c['Key']['value']: c['Value'] for c in councilors}
    nation_map_data    = _nation_map(db_path)

    # Build region → nation name map for location resolution
    regions = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIRegionState')
    region_map = {r['Key']['value']: r['Value'] for r in regions}
    region_nation = {}
    for nk, n in nation_map_data.items():
        for rk in (r.get('value') for r in n.get('regions', [])):
            region_nation[rk] = nk

    def resolve_location(loc: dict) -> str:
        if not loc:
            return 'unknown'
        loc_type = loc.get('$type', '')
        loc_key  = loc.get('value')
        if 'Region' in loc_type:
            region = region_map.get(loc_key, {})
            nation_key = region_nation.get(loc_key)
            nation = nation_map_data.get(nation_key, {})
            region_name = region.get('displayName', f'region {loc_key}')
            nation_name = nation.get('displayName', '')
            return f"{region_name}, {nation_name}" if nation_name else region_name
        elif 'Hab' in loc_type:
            return f'hab {loc_key}'
        return 'unknown'

    # Build internalCouncilorSuspicion map
    suspicion_map: dict[int, tuple[str, float]] = {}
    for f in factions:
        v = f['Value']
        fname = v.get('displayName', '?')
        for entry in v.get('internalCouncilorSuspicion', []):
            ck  = entry['Key']['value']
            sus = entry['Value']
            if ck not in suspicion_map or sus > suspicion_map[ck][1]:
                suspicion_map[ck] = (fname, sus)

    lines = ["# INTELLIGENCE STATE", ""]

    # Known enemy councilors
    intel_entries = pf.get('intel', [])
    enemy_councilor_intel = [
        (entry['Key']['value'], entry['Value'])
        for entry in intel_entries
        if 'TICouncilorState' in entry['Key'].get('$type', '')
        and (councilor_map.get(entry['Key']['value'], {}).get('faction') or {}).get('value') != player_faction_key
    ]

    lines.append("## Known Enemy Councilors")
    lines.append(f"  {'Name':<25} {'Type':<16} {'Faction':<22} {'Intel':>6}  {'Suspicion':>9}  Location")
    lines.append("  " + "-" * 100)

    enemy_councilor_intel.sort(key=lambda x: (
        faction_names.get((councilor_map.get(x[0], {}).get('faction') or {}).get('value'), '?'),
        councilor_map.get(x[0], {}).get('displayName', '')
    ))

    for ck, intel_level in enemy_councilor_intel:
        c = councilor_map.get(ck, {})
        if not c:
            continue
        name     = c.get('displayName', '?')
        ctype    = c.get('typeTemplateName', '?')
        fk       = (c.get('faction') or {}).get('value')
        fname    = faction_names.get(fk, '?')
        location = resolve_location(c.get('location', {}))
        sus_val  = suspicion_map.get(ck, ('', 0.0))[1]
        sus_str  = f"{sus_val:.1f}" if sus_val > 0 else '-'
        intel_str = f"{intel_level:.2f}"
        lines.append(
            f"  {name:<25} {ctype:<16} {fname:<22} {intel_str:>6}  {sus_str:>9}  {location}"
        )

    if not enemy_councilor_intel:
        lines.append("  No enemy councilors identified yet")

    # Faction intel levels
    faction_intel = [
        (entry['Key']['value'], entry['Value'])
        for entry in intel_entries
        if 'TIFactionState' in entry['Key'].get('$type', '')
    ]

    if faction_intel:
        lines += ["", "## Faction Intel Levels"]
        for fk, level in sorted(faction_intel, key=lambda x: -x[1]):
            mark = " *" if fk == player_faction_key else ""
            lines.append(f"  {faction_names.get(fk, '?'):<22}{mark}  {level:.2f}")

    # Our councilors
    player_councilor_keys = {c['value'] for c in pf.get('councilors', [])}
    player_councilors = [councilor_map[k] for k in player_councilor_keys if k in councilor_map]

    lines += ["", "## Our Councilors"]
    lines.append(f"  {'Name':<25} {'Type':<16} Location")
    lines.append("  " + "-" * 70)
    for c in sorted(player_councilors, key=lambda x: x.get('displayName', '')):
        location = resolve_location(c.get('location', {}))
        lines.append(
            f"  {c.get('displayName','?'):<25} "
            f"{c.get('typeTemplateName','?'):<16} "
            f"{location}"
        )

    out.write_text("\n".join(lines), encoding='utf-8')
    return out.stat().st_size // 1024
