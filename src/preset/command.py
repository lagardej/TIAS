"""
Preset command - Extract game state into domain-specific context files

Writes four focused files to campaigns/{faction}/{iso_date}/:
  gamestate_earth.txt    - nations, CPs, climate, nuclear, faction resources (with history deltas)
  gamestate_space.txt    - habs, stations, fleets, launch windows
  gamestate_intel.txt    - known enemy councilors, faction intel, our councilors
  gamestate_research.txt - finished techs, global research state

Extractors live in preset/extractors/ for clean separation.
"""

import json
import logging
import sqlite3
from pathlib import Path

from src.core.core import get_project_root
from src.core.date_utils import parse_flexible_date
from src.perf.performance import timed_command

# Import domain extractors
from src.preset.extractors.earth import write_earth
from src.preset.extractors.space import write_space
from src.preset.extractors.intel import write_intel
from src.preset.extractors.research import write_research


# ---------------------------------------------------------------------------
# Shared helpers (passed to extractors)
# ---------------------------------------------------------------------------

def _load_gs(db_path: Path, key: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM gamestates WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []


def _player_faction(db_path: Path) -> tuple[int, dict]:
    players = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIPlayerState')
    human = next(p for p in players if not p['Value']['isAI'])
    faction_key = human['Value']['faction']['value']
    factions = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    pf = next(f['Value'] for f in factions if f['Key']['value'] == faction_key)
    return faction_key, pf


def _faction_name_map(db_path: Path) -> dict[int, str]:
    factions = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    return {f['Key']['value']: f['Value'].get('displayName', '?') for f in factions}


def _nation_map(db_path: Path) -> dict[int, dict]:
    nations = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TINationState')
    return {n['Key']['value']: n['Value'] for n in nations}


def _hab_body_map(db_path: Path) -> dict[int, str]:
    """hab_key → body display name"""
    sites  = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabSiteState')
    bodies = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TISpaceBodyState')
    body_name = {b['Key']['value']: b['Value'].get('displayName', '?') for b in bodies}
    site_body  = {s['Key']['value']: body_name.get(s['Value'].get('parentBody', {}).get('value'), '?')
                  for s in sites}
    habs = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabState')
    return {
        h['Key']['value']: site_body.get((h['Value'].get('habSite') or {}).get('value'), '?')
        for h in habs
    }


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

@timed_command
def cmd_preset(args):
    """Extract game state into domain-specific context files"""
    project_root = get_project_root()

    game_date, iso_date = parse_flexible_date(args.date)
    faction = args.faction

    templates_db   = project_root / "build" / "game_templates.db"
    savegame_db    = project_root / "build" / f"savegame_{iso_date}.db"
    templates_file = project_root / "build" / "templates" / "TISpaceBodyTemplate.json"

    # Output directory: campaigns/{faction}/{iso_date}/
    output_dir = project_root / "campaigns" / faction / iso_date
    output_dir.mkdir(parents=True, exist_ok=True)

    if not templates_db.exists():
        logging.error("Templates DB missing. Run: tias load")
        return 1

    if not savegame_db.exists():
        logging.error(f"Savegame DB missing. Run: tias stage --date {args.date}")
        return 1

    # Bundle helpers for extractors
    helpers = {
        'load_gs': _load_gs,
        'player_faction': _player_faction,
        'faction_name_map': _faction_name_map,
        'nation_map': _nation_map,
        'hab_body_map': _hab_body_map,
    }

    logging.info(f"Extracting game state to {output_dir.name}/...")

    kb_earth    = write_earth(savegame_db, output_dir / "gamestate_earth.txt", helpers)
    kb_space    = write_space(savegame_db, output_dir / "gamestate_space.txt", game_date, templates_file, helpers)
    kb_intel    = write_intel(savegame_db, output_dir / "gamestate_intel.txt", helpers)
    kb_research = write_research(savegame_db, output_dir / "gamestate_research.txt", helpers)

    files = list(output_dir.glob("gamestate_*.txt"))
    total_kb = sum(f.stat().st_size for f in files) // 1024
    
    logging.info(f"[OK] Preset complete: {len(files)} domain files, {total_kb}KB total")
    print(f"\n[OK] Preset complete: {len(files)} domain files ({total_kb}KB total)")
    for fname, kb in [
        ("gamestate_earth.txt", kb_earth),
        ("gamestate_space.txt", kb_space),
        ("gamestate_intel.txt", kb_intel),
        ("gamestate_research.txt", kb_research)
    ]:
        print(f"     {fname} ({kb}KB)")
