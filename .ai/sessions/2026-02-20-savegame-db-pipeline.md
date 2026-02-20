# Session: savegame.db Pipeline
**Date:** 2026-02-20
**Status:** Complete

## What was built

### New files
- `src/db/__init__.py`
- `src/db/schema.py` — SQLite schema for savegame.db (V1) and campaign.db
- `src/db/populate.py` — Populates savegame.db from raw parse DB
- `src/db/query.py` — SQL queries → CODEX report text (replaces gamestate_*.txt)

### Modified files
- `src/stage/command.py` — Phase 2b: calls `populate_savegame_db` after tier evaluation
- `src/orchestrator/prompt_assemble.py` — `_load_gamestate` now reads savegame.db first, falls back to txt

## Schema (V1) — savegame.db
Located at `campaigns/{faction}/{date}/savegame.db`

Tables:
- `meta` — schema_version, iso_date, faction_slug, faction_display, faction_key, generated_at
- `gs_global` — co2_ppm, sea_level_anomaly, nuclear_strikes, loose_nukes (single row, id=1)
- `gs_nations` — all active nations (capital filter), gdp_t, unrest, democracy, nukes
- `gs_control_points` — cp_key, nation_key, faction_key, faction_name, cp_type, is_player
- `gs_public_opinion` — all active nations, all 8 stances (resist/destroy/exploit/submit/appease/cooperate/escape/undecided)
- `gs_federations` — fed_key, name, member_count, major_power_count
- `gs_faction_resources` — money, influence, ops, boost, mc_cap per faction
- `gs_councilors_enemy` — known enemies, resolved locations
- `gs_councilors_player` — our councilors, resolved locations
- `gs_faction_intel` — intel levels per faction
- `gs_research_completed` — finished tech names
- `gs_habs` — parent_body_key, parent_body_name, hab_type, tier, faction
- `gs_fleets` — name, faction, location (resolved via barycenter)
- `gs_launch_windows` — destination, next_window_date, days_away, penalty_pct

## Key decisions
- Faction key resolved at runtime via TIFactionState + TIPlayerState.isAI=false — no hardcoding
- Nations filtered by `capital` field (null = not yet in play)
- Public opinion keys = faction ideologyName capitalised (Resist, Destroy, Exploit, Submit, Appease, Cooperate, Escape, Undecided)
- Habs: outposts use habSite→parentBody, stations use barycenter directly
- Councillor locations resolved via TIRegionState → nation displayName
- FK violations on gs_control_points silently skipped (alien nation CPs)
- gs_public_opinion covers all active nations (not just player-controlled)
- Schema versioned — V2 will add fleet combat, alien presence, war state

## Verified output (2027-08-01, resist)
- 294 nations inserted, ~290 with public opinion
- 523 control points
- 7 factions + aliens in resources
- 24 habs (body resolved for all)
- 5 alien fleets
- 3 launch windows (Mars 519d/32%, Sisyphus 1d, Hephaistos 0d)
- CODEX live: reads from savegame.db, confirmed CO2/sea level/nations correct

## Next session agenda
1. Add gs_space_bodies table — integrate launch_windows into it
2. Restructure campaigns/{faction}: remove date subdirectory, rename savegame.db → savegame_{date}.db
   - All path references in stage/command.py, play/command.py, orchestrator.py, query.py need updating
