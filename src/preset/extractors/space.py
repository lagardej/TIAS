"""
Space domain extractor: habs, stations, fleets, launch windows.
"""

from pathlib import Path
from src.preset.launch_windows import calculate_launch_windows


def write_space(db_path: Path, out: Path, game_date, templates_file: Path, helpers: dict):
    """Extract space game state.
    
    Args:
        db_path: Path to savegame DB
        out: Output file path
        game_date: datetime.date object for launch window calculations
        templates_file: Path to TISpaceBodyTemplate.json
        helpers: Dict of shared helper functions
    """
    _load_gs = helpers['load_gs']
    _player_faction = helpers['player_faction']
    _faction_name_map = helpers['faction_name_map']
    _hab_body_map = helpers['hab_body_map']
    
    faction_names = _faction_name_map(db_path)
    hab_body      = _hab_body_map(db_path)
    player_faction_key, _ = _player_faction(db_path)

    habs   = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabState')
    fleets = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TISpaceFleetState')
    bodies = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TISpaceBodyState')
    body_name = {b['Key']['value']: b['Value'].get('displayName', '?') for b in bodies}

    lines = ["# SPACE STATE", ""]

    # Habs by body
    hab_by_body: dict[str, list] = {}
    for h in habs:
        v = h['Value']
        if not v.get('exists') or v.get('archived'):
            continue
        body = hab_body.get(h['Key']['value'], '?')
        hab_by_body.setdefault(body, []).append(h)

    lines.append("## Habs & Stations")
    for body in sorted(hab_by_body.keys()):
        lines.append(f"\n### {body}")
        lines.append(f"  {'Name':<30} {'Type':<10} {'Tier':<5} {'Faction'}")
        lines.append("  " + "-" * 65)
        for h in sorted(hab_by_body[body], key=lambda x: x['Value'].get('displayName', '')):
            v = h['Value']
            fname = faction_names.get((v.get('faction') or {}).get('value'), 'None')
            player_mark = " *" if (v.get('faction') or {}).get('value') == player_faction_key else ""
            lines.append(
                f"  {v.get('displayName','?'):<30} "
                f"{v.get('habType','?'):<10} "
                f"T{v.get('tier',0)}    "
                f"{fname}{player_mark}"
            )

    # Fleets
    lines += ["", "## Fleets"]
    active_fleets = [f for f in fleets if f['Value'].get('exists') and not f['Value'].get('archived')
                     and not f['Value'].get('dummyFleet')]
    if active_fleets:
        lines.append(f"  {'Name':<25} {'Faction':<20} {'Location'}")
        lines.append("  " + "-" * 65)
        for f in sorted(active_fleets, key=lambda x: x['Value'].get('displayName', '')):
            v = f['Value']
            fname = faction_names.get((v.get('faction') or {}).get('value'), '?')
            barycenter_key = (v.get('barycenter') or {}).get('value')
            docked_key = (v.get('dockedLocation') or {}).get('value')
            if docked_key:
                location = f"docked @ hab {docked_key}"
            elif barycenter_key:
                location = f"orbiting {body_name.get(barycenter_key, f'body {barycenter_key}')}"
            else:
                location = "in transit"
            player_mark = " *" if (v.get('faction') or {}).get('value') == player_faction_key else ""
            lines.append(f"  {v.get('displayName','?'):<25} {fname:<20} {location}{player_mark}")
    else:
        lines.append("  No active fleets")

    # Launch windows
    launch_windows = calculate_launch_windows(game_date, templates_file)
    if launch_windows:
        lines += ["", "## Launch Windows"]
        for target, data in launch_windows.items():
            line = (f"  {target}: next window {data['next_window']} "
                    f"({data['days_away']} days, ~{data['days_away'] // 30} months)")
            if 'current_penalty' in data:
                line += f", current penalty {data['current_penalty']}%"
            lines.append(line)

    out.write_text("\n".join(lines), encoding='utf-8')
    return out.stat().st_size // 1024
