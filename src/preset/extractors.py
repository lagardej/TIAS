"""
Shared extraction helpers for game state domain modules
"""

import json
import sqlite3
from pathlib import Path


def load_gs(db_path: Path, key: str):
    """Load one gamestate array from the DB, parsed from JSON."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM gamestates WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []


def player_faction(db_path: Path) -> tuple[int, dict]:
    """Return (faction_key, faction_value) for the human player."""
    players = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIPlayerState')
    human = next(p for p in players if not p['Value']['isAI'])
    faction_key = human['Value']['faction']['value']
    factions = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    pf = next(f['Value'] for f in factions if f['Key']['value'] == faction_key)
    return faction_key, pf


def faction_name_map(db_path: Path) -> dict[int, str]:
    """Return {faction_key: display_name}."""
    factions = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    return {f['Key']['value']: f['Value'].get('displayName', '?') for f in factions}


def nation_map(db_path: Path) -> dict[int, dict]:
    """Return {nation_key: nation_value}."""
    nations = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TINationState')
    return {n['Key']['value']: n['Value'] for n in nations}


def hab_body_map(db_path: Path) -> dict[int, str]:
    """Return {hab_key: body_display_name} for all habs that have a site."""
    sites  = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabSiteState')
    bodies = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TISpaceBodyState')
    body_name = {b['Key']['value']: b['Value'].get('displayName', '?') for b in bodies}
    site_body  = {s['Key']['value']: body_name.get(s['Value'].get('parentBody', {}).get('value'), '?')
                  for s in sites}
    habs = load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabState')
    return {
        h['Key']['value']: site_body.get((h['Value'].get('habSite') or {}).get('value'), '?')
        for h in habs
    }
