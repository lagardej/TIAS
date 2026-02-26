# Session: gs_hab_modules — Hab Module Table
**Date:** 2026-02-21
**Status:** Complete

## Objective
Item #1 from backlog: add `gs_hab_modules` to the savegame DB pipeline.
Unblocks Jonny for "what can I build now" queries and hab state assessment.

## What was built

### Schema (`src/db/schema.py`)
New table `gs_hab_modules`:
```sql
module_key          INTEGER PK   -- TIHabModuleState key
hab_key             INTEGER FK   -- → gs_habs
module_name         TEXT         -- TIHabModuleTemplate dataName (templateName in save)
display_name        TEXT         -- localized display name from save
tier                INTEGER      -- from TIHabModuleTemplate
crew                INTEGER      -- from TIHabModuleTemplate (positive = requires)
power               INTEGER      -- from TIHabModuleTemplate (negative = consuming)
construction_completed INTEGER   -- 0 if still building
completion_date     TEXT         -- ISO date: ETA if building, actual if complete
powered             INTEGER      -- 0 if unpowered
destroyed           INTEGER
```
Indexes: `idx_hab_modules_hab`, `idx_hab_modules_name`

### Populate (`src/db/populate.py`)
- Added `templates_dir: Path | None` param to `populate_savegame_db` and `_populate_space`
- New function `_populate_hab_modules(conn, raw_db, _load_gs, templates_dir)`:
  - Loads `TIHabModuleTemplate.json` → `{dataName: {tier, crew, power}}` lookup
  - Builds `sector_key → hab_key` map from `TISectorState`
  - Iterates `TIHabModuleState`, skips vacant slots (empty templateName), resolves hab via sector
  - Inserts with template-enriched tier/crew/power values
- `_clear_snapshot` updated to include `gs_hab_modules`
- Called after hab insertion (FK dependency satisfied)

### Stage (`src/stage/command.py`)
- `templates_dir` now derived from `templates_file` path and passed to `populate_savegame_db`

### Query (`src/db/query.py`)
- `_section_habs`: added module summary columns (Mod active/total, Crew, Pwr) to hab table
- New `_section_hab_modules`: detailed per-player-hab module listing with status
  (active / BUILDING ETA / UNPOWERED / DESTROYED)
- Both added to `build_codex_report`

## Data model findings (from raw save inspection)
- `TIHabModuleState`: 504 total entries, 147 with non-empty templateName (occupied slots)
- 100% resolution rate: all 147 modules resolved to a hab via sector → hab chain
- Join chain: `TIHabModuleState.sector.value` → `TISectorState.hab.value` → `gs_habs.hab_key`
- Vacant slots have `templateName = ""` — skipped cleanly
- `completionDate` present on both completed and in-progress modules; `0001-*` dates = null/never
- Under-construction modules have `constructionCompleted: false` and future `completionDate`
- Destroyed modules have `destroyed: true` and may carry a prior module's `templateName`

## Power sign convention
- Template `power` field: negative = consuming, positive = generating
- Confirmed from template read: `AdministrationNode` has `power: -10`

## Key decision: templates_dir over individual file paths
Previous pattern was to pass individual template file paths. Switched to passing the
`templates_dir` directory once, so future template lookups (tech, project system) can
reuse the same pattern without adding more params.

## Verified against 2027-08-01 save
- 24 habs in save, 147 occupied module slots across them
- Populate logic resolves correctly (all 147 → hab_key)
- Template file (`build/templates/TIHabModuleTemplate.json`) exists and is in expected format

## Files modified
- `src/db/schema.py` — added `gs_hab_modules` table + indexes
- `src/db/populate.py` — added `_populate_hab_modules`, `templates_dir` param plumbing
- `src/stage/command.py` — `templates_dir` derivation and passing
- `src/db/query.py` — `_section_habs` enhanced + `_section_hab_modules` added

## Next session candidates (from backlog)
- #2: `gs_tech` — tech status table (researched/available/locked) from TITechTemplate prereqs
- #3: Project system cross-reference — TIProjectTemplate → modules + techs
- #4: `gs_faction_resources` income breakdown
- #5: `gs_nations` additions (priority_profile, institutional_control)
