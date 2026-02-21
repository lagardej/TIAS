# Session: gs_space_bodies + Path Refactor
**Date:** 2026-02-21
**Status:** Complete

## What was built

### Path refactor (campaigns/{faction}/ flat structure)
- Removed date subdirectory from campaign output
- `savegame_{date}.db` — one per game date, side-by-side comparison supported
- `tier_state_{date}.json` — one per game date
- `context_*.txt` — dateless, always overwritten (derived from resources + tier)
- Decision: KISS now, no cross-date aggregation yet

**Files modified:**
- `src/stage/command.py` — output_dir, evaluate_tier signature, savegame_db path
- `src/play/command.py` — tier_state_path
- `src/orchestrator/orchestrator.py` — removed campaigns_dir, campaign_dir is now the flat path, date passed to prompt_assemble
- `src/orchestrator/prompt_assemble.py` — _load_gamestate, _codex_report_or_stage_direction, prompt_assemble all take date param
- `.ai/instructions.md` — file org section updated

### gs_space_bodies table
Full catalog of 373 bodies from TISpaceBodyState + TISpaceBodyTemplate.

**Schema:**
- `body_key` INTEGER PK
- `name` TEXT
- `object_type` TEXT — from template (Star, Planet, Moon, Asteroid, DwarfPlanet, etc.)
- `barycenter_key` INTEGER — parent body (null for Sol)
- `max_hab_tier` INTEGER
- `has_hab_sites` INTEGER — 1 if habSites non-empty
- `next_window_date` TEXT — nullable (absorbed from gs_launch_windows)
- `days_away` INTEGER — nullable
- `penalty_pct` REAL — nullable

**gs_launch_windows dropped** — data absorbed into gs_space_bodies.

**gs_fleets** — added `body_key` FK to gs_space_bodies.

**gs_habs query** — now joins gs_space_bodies for body name instead of using denormalised column.

### Bug fixes
- `calculate_launch_windows` keys corrected: `Sisyphus` → `1866 Sisyphus`, `Hephaistos` → `2212 Hephaistos` to match TISpaceBodyState displayName

## Verified output (2027-08-01, resist)
- 373 space bodies inserted
- Mars, 1866 Sisyphus, 2212 Hephaistos have launch window data
- gs_fleets body_key populated
- CODEX report reads correctly from new schema

## Key decisions
- One DB per game date (option A) — simplest, matches game save model, cross-date analysis deferred
- context_*.txt always overwritten — derived data, no value in versioning
- gs_space_bodies is full catalog (all 373 bodies) — advisors need full list for target selection; CODEX filters by faction assets

## Next session candidates
- Councillor location for habs (currently `hab {key}`, not a name)
- CODEX report tuning — filter/format improvements now that space bodies are queryable
- V2 schema planning — fleet combat, alien presence, war state
