"""
Stage command - Parse savegame, evaluate tier, assemble actor context files

The core domain logic command. Three phases in sequence:

  1. PARSE   - load savegame DB (skipped if DB is current)
  2. EVALUATE - calculate tier readiness from game state, write tier_state.json
  3. ASSEMBLE - combine resources/ + tier → generated/{iso_date}/context_*.txt

Usage:
  tias stage --date 2027-8-1
  tias stage --date 2027-8-1 --force   # re-parse even if DB is current
"""

import json
import logging
import sqlite3
import tomllib
from datetime import datetime
from pathlib import Path

from src.core.core import load_env, get_project_root
from src.core.date_utils import parse_flexible_date
from src.perf.performance import timed_command

# Stable Terra Invicta body keys (confirmed across saves)
BODY_LUNA    = 6
BODY_MARS    = 7
BODY_JUPITER = 10   # >= this value = Jupiter system or beyond

# Major power GDP threshold (stub - refine from game data when observed)
MAJOR_POWER_GDP_THRESHOLD = 1_000_000_000_000  # 1 trillion


# ---------------------------------------------------------------------------
# Phase 1: Parse-if-stale
# ---------------------------------------------------------------------------

def _db_is_stale(db_path: Path, saves_dir: Path, game_date) -> bool:
    """Return True if savegame DB is missing or older than the .gz file."""
    if not db_path.exists():
        return True

    game_format = f"{game_date.year}-{game_date.month}-{game_date.day}"
    matches = list(saves_dir.glob(f"*_{game_format}.gz"))
    if not matches:
        return False  # can't find the source, don't re-parse

    gz_mtime = matches[0].stat().st_mtime
    db_mtime = db_path.stat().st_mtime
    return gz_mtime > db_mtime


def _ensure_db(project_root: Path, game_date, iso_date: str, force: bool) -> Path:
    """Parse savegame into DB if missing, stale, or forced. Return db_path."""
    from src.parse.command import parse_savegame, find_savegame

    env = load_env()
    saves_dir = Path(env['GAME_SAVES_DIR'])
    db_path = project_root / "build" / f"savegame_{iso_date}.db"

    if force or _db_is_stale(db_path, saves_dir, game_date):
        logging.info("Parsing savegame...")
        n_keys = parse_savegame(saves_dir, game_date, db_path)
        db_size = db_path.stat().st_size / 1024 / 1024
        logging.info(f"  Parsed: {db_path.name} ({db_size:.1f}MB, {n_keys} keys)")
    else:
        logging.info(f"Savegame DB current: {db_path.name}")

    return db_path


# ---------------------------------------------------------------------------
# Phase 2: Tier evaluation
# ---------------------------------------------------------------------------

def _load_gs(db_path: Path, key: str):
    """Load one gamestate array from the DB, parsed from JSON."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM gamestates WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []


def _find_player_faction(db_path: Path) -> tuple[int, dict]:
    """Return (faction_key, faction_value) for the human player."""
    players = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIPlayerState')
    human = next((p for p in players if not p['Value']['isAI']), None)
    if not human:
        raise ValueError("No human player found in savegame")

    faction_key = human['Value']['faction']['value']
    factions = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFactionState')
    pf = next((f['Value'] for f in factions if f['Key']['value'] == faction_key), None)
    if not pf:
        raise ValueError(f"Player faction {faction_key} not found in TIFactionState")

    return faction_key, pf


def _build_hab_body_map(db_path: Path) -> dict:
    """Return {hab_key: body_display_name} for all habs that have a site."""
    sites = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabSiteState')
    bodies = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TISpaceBodyState')

    body_name = {b['Key']['value']: b['Value'].get('displayName', '') for b in bodies}
    site_body = {s['Key']['value']: body_name.get(s['Value'].get('parentBody', {}).get('value'))
                 for s in sites}

    habs = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabState')
    hab_body = {}
    for h in habs:
        site_key = h['Value'].get('habSite', {})
        if site_key:
            site_key = site_key.get('value')
        hab_body[h['Key']['value']] = site_body.get(site_key, '')

    return hab_body


def evaluate_tier(db_path: Path, generated_dir: Path) -> dict:
    """
    Evaluate tier readiness from savegame DB.
    Writes tier_state.json to generated_dir.
    Returns the state dict.
    """
    faction_key, pf = _find_player_faction(db_path)
    hab_body = _build_hab_body_map(db_path)

    # --- Player habs ---
    all_habs = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIHabState')
    player_habs = [h for h in all_habs
                   if h['Value'].get('faction', {}).get('value') == faction_key]

    # --- Player councilors on habs ---
    councilor_keys = {c['value'] for c in pf.get('councilors', [])}
    all_councilors = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TICouncilorState')
    player_councilors = [c for c in all_councilors
                         if c['Key']['value'] in councilor_keys]
    councilors_on_habs = {
        c['Value']['location']['value']
        for c in player_councilors
        if 'TIHabState' in c['Value'].get('location', {}).get('$type', '')
    }

    # --- Player fleets ---
    fleet_keys = {f['value'] for f in pf.get('fleets', [])}
    all_fleets = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TISpaceFleetState')
    player_fleets = [f for f in all_fleets if f['Key']['value'] in fleet_keys]

    # --- Player nations (via control points) ---
    cp_keys = {cp['value'] for cp in pf.get('controlPoints', [])}
    all_cps = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIControlPoint')
    player_nation_keys = {
        cp['Value']['nation']['value']
        for cp in all_cps
        if cp['Key']['value'] in cp_keys
    }

    # --- Nation and federation data ---
    all_nations = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TINationState')
    nation_map = {n['Key']['value']: n['Value'] for n in all_nations}

    all_feds = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIFederationState')
    fed_map = {f['Key']['value']: f['Value'] for f in all_feds}

    # -----------------------------------------------------------------------
    # Evaluate Tier 2 conditions
    # -----------------------------------------------------------------------

    # C1: Operative on Luna or Mars mine (Base hab on Luna/Mars with councilor aboard)
    luna_mars_mines = {
        h['Key']['value'] for h in player_habs
        if h['Value'].get('habType') == 'Base'
        and hab_body.get(h['Key']['value']) in ('Luna', 'Mars')
    }
    c1_luna_mars_mine = bool(councilors_on_habs & luna_mars_mines)

    # C2: Operative on Earth shipyard (councilor on LEO station with shipyard module)
    # TODO: confirm shipyard module templateName when one is built in-game
    # For now: councilor on any player-owned Earth LEO station
    earth_leo_stations = {
        h['Key']['value'] for h in player_habs
        if h['Value'].get('habType') == 'Station'
        and h['Value'].get('inEarthLEO')
    }
    c2_earth_shipyard = bool(councilors_on_habs & earth_leo_stations)

    # C3: 10+ MC capacity
    mc_capacity = pf.get('baseIncomes_year', {}).get('MissionControl', 0)
    c3_mc_10 = mc_capacity >= 10

    # C4: Control 3+ space stations
    stations = [h for h in player_habs if h['Value'].get('habType') == 'Station']
    c4_stations_3 = len(stations) >= 3

    # C5: Member of 3+ nation federation
    c5_federation_3 = False
    for nk in player_nation_keys:
        nation = nation_map.get(nk, {})
        if nation.get('aggregateNation'):
            continue  # skip federation-as-nation entries
        fed_ref = nation.get('federation')
        if fed_ref:
            fed_key = fed_ref.get('value') if isinstance(fed_ref, dict) else fed_ref
            fed = fed_map.get(fed_key, {})
            if len(fed.get('members', [])) >= 3:
                c5_federation_3 = True
                break

    tier2_conditions = {
        'luna_mars_mine':   c1_luna_mars_mine,
        'earth_shipyard':   c2_earth_shipyard,
        'mc_10plus':        c3_mc_10,
        'stations_3plus':   c4_stations_3,
        'federation_3plus': c5_federation_3,
    }
    tier2_met = sum(tier2_conditions.values())
    tier2_needed = 2
    tier2_unlocked = tier2_met >= tier2_needed

    # -----------------------------------------------------------------------
    # Evaluate Tier 3 conditions
    # -----------------------------------------------------------------------

    # D1: Control orbital ring or space elevator
    # TODO: confirm habType/module name — not observed in early save
    d1_orbital_ring = False  # stub

    # D2: Fleet in Jupiter system or beyond
    d2_jupiter_fleet = any(
        (f['Value'].get('barycenter') or {}).get('value', 0) >= BODY_JUPITER
        for f in player_fleets
    )

    # D3: 25+ MC capacity
    d3_mc_25 = mc_capacity >= 25

    # D4: Control 10+ habs
    d4_habs_10 = len(player_habs) >= 10

    # D5: Federation of 5+ major powers
    # Major power stub: GDP > threshold
    d5_major_fed = False
    for nk in player_nation_keys:
        nation = nation_map.get(nk, {})
        if nation.get('aggregateNation'):
            continue
        fed_ref = nation.get('federation')
        if fed_ref:
            fed_key = fed_ref.get('value') if isinstance(fed_ref, dict) else fed_ref
            fed = fed_map.get(fed_key, {})
            major_members = sum(
                1 for mk in (m['value'] for m in fed.get('members', []))
                if nation_map.get(mk, {}).get('GDP', 0) >= MAJOR_POWER_GDP_THRESHOLD
                and not nation_map.get(mk, {}).get('aggregateNation')
            )
            if major_members >= 5:
                d5_major_fed = True
                break

    # D6: Councilor mission success rate >80% (stub - mission history not yet parsed)
    d6_mission_success = False  # stub

    tier3_conditions = {
        'orbital_ring':     d1_orbital_ring,
        'jupiter_fleet':    d2_jupiter_fleet,
        'mc_25plus':        d3_mc_25,
        'habs_10plus':      d4_habs_10,
        'major_federation': d5_major_fed,
        'mission_success':  d6_mission_success,
    }
    tier3_met = sum(tier3_conditions.values())
    tier3_needed = 3
    tier3_unlocked = tier3_met >= tier3_needed

    # -----------------------------------------------------------------------
    # Determine current tier
    # -----------------------------------------------------------------------
    if tier3_unlocked:
        current_tier = 3
    elif tier2_unlocked:
        current_tier = 2
    else:
        current_tier = 1

    # Overall readiness: fraction of highest unlocked tier's next threshold
    if current_tier == 3:
        readiness = 1.0
    elif current_tier == 2:
        readiness = 0.6 + 0.1 * (tier3_met / tier3_needed)
    else:
        readiness = 0.0 + 0.6 * (tier2_met / tier2_needed)

    state = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'current_tier': current_tier,
        'readiness': round(readiness, 3),
        'mc_capacity': mc_capacity,
        'hab_count': len(player_habs),
        'station_count': len(stations),
        'tier2_conditions': tier2_conditions,
        'tier2_met': tier2_met,
        'tier2_needed': tier2_needed,
        'tier2_unlocked': tier2_unlocked,
        'tier3_conditions': tier3_conditions,
        'tier3_met': tier3_met,
        'tier3_needed': tier3_needed,
        'tier3_unlocked': tier3_unlocked,
        'stubs': ['earth_shipyard', 'orbital_ring', 'mission_success'],
    }

    out = generated_dir / 'tier_state.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

    logging.info(f"Tier evaluated: {current_tier} "
                 f"(readiness {readiness:.0%}, "
                 f"T2: {tier2_met}/{tier2_needed}, "
                 f"T3: {tier3_met}/{tier3_needed})")

    return state


# ---------------------------------------------------------------------------
# Phase 3: Assemble actor contexts
# ---------------------------------------------------------------------------

def load_actor(actor_dir: Path) -> dict:
    """Load all files for one actor into a dict."""
    spec_file = actor_dir / "spec.toml"
    if not spec_file.exists():
        return {}

    with open(spec_file, 'rb') as f:
        actor = tomllib.load(f)

    for filename, key in [
        ('background.txt',  'background'),
        ('personality.txt', 'personality'),
        ('stage.txt',       'stage_directions'),
    ]:
        filepath = actor_dir / filename
        actor[key] = filepath.read_text(encoding='utf-8').strip() if filepath.exists() else ''

    for tier in (1, 2, 3):
        filepath = actor_dir / f"examples_tier{tier}.md"
        actor[f'examples_tier{tier}'] = (
            filepath.read_text(encoding='utf-8').strip() if filepath.exists() else ''
        )

    return actor


def assemble_actor_context(actor: dict, tier: int) -> str:
    """Assemble a single actor's context file for the given tier."""
    name         = actor.get('display_name', actor.get('name', 'Unknown'))
    domain       = actor.get('domain_primary', '')
    tier_scope   = actor.get(f'tier_{tier}_scope', '')
    can_discuss  = actor.get(f'tier_{tier}_can_discuss', '')
    cannot       = actor.get(f'tier_{tier}_cannot_discuss', '')
    err_domain   = actor.get('error_domain_mismatch', '')
    err_tier     = actor.get(f'error_out_of_tier_{tier}', '')
    background   = actor.get('background', '')
    personality  = actor.get('personality', '')
    stage_dirs   = actor.get('stage_directions', '')
    examples     = actor.get(f'examples_tier{tier}', '')

    lines = [f"## {name}"]
    if domain:       lines += [f"Domain: {domain}", ""]
    if background:   lines += ["### Background", background, ""]
    if personality:  lines += ["### Personality", personality, ""]
    if tier_scope:   lines += [f"### Tier {tier} Scope", tier_scope, ""]
    if can_discuss:  lines += ["### Can Discuss", can_discuss, ""]
    if cannot:       lines += ["### Cannot Discuss", cannot, ""]
    if err_tier:     lines += ["### Out of Tier Response", err_tier, ""]
    if err_domain:   lines += ["### Out of Domain Response", err_domain, ""]
    if stage_dirs:   lines += ["### Stage Directions", stage_dirs, ""]
    if examples:     lines += [f"### Example Exchanges (Tier {tier})", examples, ""]

    return "\n".join(lines)


def assemble_system_context(prompts_dir: Path, tier: int) -> str:
    """Assemble the global system prompt."""
    system_file = prompts_dir / "system.txt"
    if not system_file.exists():
        logging.warning("resources/prompts/system.txt not found - skipping")
        return ''
    content = system_file.read_text(encoding='utf-8').strip()
    return f"# SYSTEM\nTier: {tier}\n\n{content}"


def assemble_codex_context(prompts_dir: Path) -> str:
    """Assemble the CODEX evaluation template."""
    codex_file = prompts_dir / "codex_eval.txt"
    if not codex_file.exists():
        logging.warning("resources/prompts/codex_eval.txt not found - skipping")
        return ''
    return codex_file.read_text(encoding='utf-8').strip()


def assemble_contexts(resources_dir: Path, generated_dir: Path, tier: int):
    """Assemble all context files at the given tier."""
    prompts_dir = resources_dir / "prompts"

    system_ctx = assemble_system_context(prompts_dir, tier)
    if system_ctx:
        (generated_dir / "context_system.txt").write_text(system_ctx, encoding='utf-8')
        logging.info("  -> context_system.txt")

    codex_ctx = assemble_codex_context(prompts_dir)
    if codex_ctx:
        (generated_dir / "context_codex.txt").write_text(codex_ctx, encoding='utf-8')
        logging.info("  -> context_codex.txt")

    assembled, skipped = [], []
    for actor_dir in sorted((resources_dir / "actors").iterdir()):
        if not actor_dir.is_dir() or actor_dir.name.startswith('_'):
            continue
        actor = load_actor(actor_dir)
        if not actor:
            skipped.append(actor_dir.name)
            continue
        ctx = assemble_actor_context(actor, tier)
        (generated_dir / f"context_{actor_dir.name}.txt").write_text(ctx, encoding='utf-8')
        assembled.append(actor_dir.name)
        logging.info(f"  -> context_{actor_dir.name}.txt")

    if skipped:
        logging.warning(f"Skipped actors (no spec.toml): {', '.join(skipped)}")

    return assembled


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------

@timed_command
def cmd_stage(args):
    """Parse savegame, evaluate tier, assemble actor context files"""
    project_root = get_project_root()
    resources_dir = project_root / "resources"
    
    game_date, iso_date = parse_flexible_date(args.date)
    force = getattr(args, 'force', False)

    # Output directory: generated/{iso_date}/
    output_dir = project_root / "generated" / iso_date
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: Parse
    db_path = _ensure_db(project_root, game_date, iso_date, force)

    # Phase 2: Evaluate
    state = evaluate_tier(db_path, output_dir)
    tier = state['current_tier']

    # Phase 3: Assemble
    assembled = assemble_contexts(resources_dir, output_dir, tier)

    # Summary
    t2 = state['tier2_conditions']
    t3 = state['tier3_conditions']
    print(f"\n[OK] Stage complete")
    print(f"     Tier {tier}  (readiness {state['readiness']:.0%})")
    print(f"     T2 conditions: {state['tier2_met']}/{state['tier2_needed']}  "
          f"[mine={'✓' if t2['luna_mars_mine'] else '·'}  "
          f"shipyard={'✓' if t2['earth_shipyard'] else '·'}  "
          f"MC={'✓' if t2['mc_10plus'] else '·'}  "
          f"stations={'✓' if t2['stations_3plus'] else '·'}  "
          f"fed={'✓' if t2['federation_3plus'] else '·'}]")
    print(f"     T3 conditions: {state['tier3_met']}/{state['tier3_needed']}  "
          f"[ring={'✓' if t3['orbital_ring'] else '·'}  "
          f"jupiter={'✓' if t3['jupiter_fleet'] else '·'}  "
          f"MC={'✓' if t3['mc_25plus'] else '·'}  "
          f"habs={'✓' if t3['habs_10plus'] else '·'}  "
          f"majfed={'✓' if t3['major_federation'] else '·'}  "
          f"missions={'✓' if t3['mission_success'] else '·'}]")
    print(f"     Actors: {', '.join(assembled)}")
