"""
Earth domain extractor: nations, control points, climate, faction resources.
"""

from pathlib import Path


def write_earth(db_path: Path, out: Path, helpers: dict):
    """Extract Earth/political game state.
    
    Args:
        db_path: Path to savegame DB
        out: Output file path
        helpers: Dict of shared helper functions from command.py
    """
    _load_gs = helpers['load_gs']
    _player_faction = helpers['player_faction']
    _faction_name_map = helpers['faction_name_map']
    _nation_map = helpers['nation_map']
    
    faction_names = _faction_name_map(db_path)
    nation_map_data = _nation_map(db_path)
    player_faction_key, _ = _player_faction(db_path)

    # Control point ownership: nation → {faction_name: count}
    all_cps = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIControlPoint')
    nation_cps: dict[int, dict[str, int]] = {}
    for cp in all_cps:
        v = cp['Value']
        nk = v.get('nation', {}).get('value')
        fk = (v.get('faction') or {}).get('value')
        if nk is None:
            continue
        nation_cps.setdefault(nk, {})
        fname = faction_names.get(fk, 'Uncontrolled') if fk else 'Uncontrolled'
        nation_cps[nk][fname] = nation_cps[nk].get(fname, 0) + 1

    # Federations
    feds = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFederationState')
    
    # Global values
    gvs_list = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIGlobalValuesState')
    gvs = gvs_list[0]['Value'] if gvs_list else {}

    lines = ["# EARTH & POLITICAL STATE", ""]

    # Climate
    co2  = gvs.get('earthAtmosphericCO2_ppm', 0)
    sl   = gvs.get('globalSeaLevelAnomaly_cm', 0)
    nucs = gvs.get('nuclearStrikes', 0)
    loose = gvs.get('looseNukes', 0)
    lines += [
        "## Global",
        f"CO2: {co2:.1f} ppm  |  Sea level anomaly: {sl:.1f} cm",
        f"Nuclear strikes: {nucs}  |  Loose nukes: {loose}",
        "",
    ]

    # Nations — only non-alien, non-aggregate, with meaningful GDP
    major_nations = sorted(
        [n for n in nation_map_data.values()
         if not n.get('alienNation') and not n.get('aggregateNation')
         and n.get('GDP', 0) > 100_000_000_000],  # >100B
        key=lambda n: n.get('GDP', 0), reverse=True
    )[:30]

    lines.append("## Nations")
    lines.append(f"{'Nation':<32} {'GDP':>8}  {'Δ':>6}  {'Unrest':>6}  {'Δ':>6}  {'Demo':>5}  {'Nukes':>5}  Control Points")
    lines.append("-" * 105)

    for n in major_nations:
        name    = n.get('displayName', '?')
        gdp     = n.get('GDP', 0) / 1e12
        unrest  = n.get('unrest', 0)
        demo    = n.get('democracy', 0)
        nukes   = n.get('numNuclearWeapons', 0)
        
        # History delta: compare last vs 5 turns ago (roughly 1 month in-game)
        gdp_hist = n.get('historyGDP', [])
        unrest_hist = n.get('historyUnrest', [])
        gdp_delta = ((gdp_hist[-1] - gdp_hist[-6]) / gdp_hist[-6] * 100) if len(gdp_hist) >= 6 and gdp_hist[-6] > 0 else 0.0
        unrest_delta = (unrest_hist[-1] - unrest_hist[-6]) if len(unrest_hist) >= 6 else 0.0

        # Find nation key from nation_map
        nk = next((k for k, v in nation_map_data.items() if v is n), None)
        cp_summary = nation_cps.get(nk, {})
        cp_str = '  '.join(f"{f}:{c}" for f, c in sorted(cp_summary.items()))

        nukes_str = str(nukes) if nukes else '-'
        gdp_d_str = f"{gdp_delta:+.1f}%" if abs(gdp_delta) > 0.01 else '-'
        unrest_d_str = f"{unrest_delta:+.2f}" if abs(unrest_delta) > 0.01 else '-'
        
        lines.append(
            f"{name:<32} {gdp:>7.2f}T  {gdp_d_str:>6}  "
            f"{unrest:>6.2f}  {unrest_d_str:>6}  "
            f"{demo:>5.1f}  {nukes_str:>5}  {cp_str}"
        )

    # Public opinion summary for player-controlled nations with delta
    cp_keys = {c['value'] for c in _player_faction(db_path)[1].get('controlPoints', [])}
    player_nation_keys = {cp['Value']['nation']['value']
                          for cp in all_cps if cp['Key']['value'] in cp_keys}

    lines += ["", "## Public Opinion (Player Nations)"]
    lines.append(f"{'Nation':<32}  Resist    Δ      Destroy   Δ      Exploit   Δ      Undecided")
    lines.append("-" * 95)
    for nk in sorted(player_nation_keys):
        n = nation_map_data.get(nk, {})
        if n.get('aggregateNation') or n.get('alienNation'):
            continue
        po = n.get('publicOpinion', {})
        po_hist = n.get('historyPublicOpinion', [])
        
        # Deltas from 5 turns ago
        po_old = po_hist[-6] if len(po_hist) >= 6 else {}
        delta_resist = (po.get('Resist', 0) - po_old.get('Resist', 0)) * 100
        delta_destroy = (po.get('Destroy', 0) - po_old.get('Destroy', 0)) * 100
        delta_exploit = (po.get('Exploit', 0) - po_old.get('Exploit', 0)) * 100
        delta_undecided = (po.get('Undecided', 0) - po_old.get('Undecided', 0)) * 100
        
        name = n.get('displayName', '?')
        lines.append(
            f"{name:<32}  "
            f"{po.get('Resist',0):>6.0%}  {delta_resist:>+6.1f}  "
            f"{po.get('Destroy',0):>7.0%}  {delta_destroy:>+6.1f}  "
            f"{po.get('Exploit',0):>7.0%}  {delta_exploit:>+6.1f}  "
            f"{po.get('Undecided',0):>8.0%}"
        )

    # Federations
    lines += ["", "## Federations"]
    for fed in feds:
        v = fed['Value']
        name = v.get('displayNameWithArticle') or v.get('displayName', '?')
        members = v.get('members', [])
        major = sum(1 for m in members
                    if nation_map_data.get(m['value'], {}).get('GDP', 0) > 1e12
                    and not nation_map_data.get(m['value'], {}).get('aggregateNation'))
        lines.append(f"{name}: {len(members)} members ({major} major powers)")

    # Faction resources
    factions = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    lines += ["", "## Faction Resources"]
    lines.append(f"  {'Faction':<22} {'Money':>10}  {'Influence':>9}  {'Ops':>6}  {'Boost':>6}  {'MC cap':>6}")
    lines.append("  " + "-" * 68)
    for f in factions:
        v = f['Value']
        if not v.get('exists') or v.get('archived'):
            continue
        name  = v.get('displayName', '?')
        res   = v.get('resources', {})
        mc    = v.get('baseIncomes_year', {}).get('MissionControl', 0)
        mark  = " *" if f['Key']['value'] == player_faction_key else ""
        lines.append(
            f"  {name:<22}{mark} "
            f"{res.get('Money', 0):>12,.0f}  "
            f"{res.get('Influence', 0):>9.0f}  "
            f"{res.get('Operations', 0):>6.0f}  "
            f"{res.get('Boost', 0):>6.0f}  "
            f"{mc:>6.0f}"
        )

    out.write_text("\n".join(lines), encoding='utf-8')
    return out.stat().st_size // 1024
