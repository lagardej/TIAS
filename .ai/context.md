# Terra Invicta Advisory System - Project Context

## What This Project Does

LLM-powered advisory system for Terra Invicta campaign gameplay. Pause at Assignment Phase → sync savegame → consult AI advisors via KoboldCpp → make decisions → play on.

**Core workflow:**
```
tias stage --date YYYY-MM-DD && tias preset --date YYYY-MM-DD && tias play --date YYYY-MM-DD
```

---

## Architecture

### Entry Point
- `tias` command installed via `pip install -e .`
- Entry point: `src/__main__.py`
- Dispatcher: argparse → `src/<command>/command.py`

### Package Structure
```
src/
├── __main__.py         # Entry point
├── core/               # Shared utilities (only package others may import)
│   ├── core.py         # get_project_root(), load_env(), setup_logging()
│   └── date_utils.py   # parse_flexible_date() → (datetime, ISO string)
├── load/               # Import game templates into SQLite
├── clean/              # Remove build/
├── install/            # Interactive setup wizard
├── parse/              # Savegame → SQLite
├── stage/              # Assemble actor context files at current tier
├── preset/             # Actor contexts + game data → LLM context
│   └── launch_windows.py  # Mars/NEA transfer window calculations
├── play/               # Launch KoboldCpp
├── validate/           # Check config and paths
└── perf/               # Performance tracking
    └── performance.py  # @timed_command decorator
```

### Pipeline
```
Terra Invicta install (read-only)
    ↓ tias load
build/templates/*.json + build/game_templates.db

Savegame (.gz)
    ↓ tias stage --date DATE  [phase 1: parse-if-stale]
build/savegame_YYYY-MM-DD.db

Savegame DB
    ↓ tias stage --date DATE  [phase 2: evaluate tier]
generated/tier_state.json

resources/actors/ + resources/prompts/ + tier_state.json
    ↓ tias stage --date DATE  [phase 3: assemble]
generated/context_*.txt (one per actor + system + codex)

context_*.txt + Templates DB + Savegame DB
    ↓ tias preset
generated/mistral_context.txt

    ↓ tias play
KoboldCpp (LLM server, localhost:5001)
```

`tias parse` remains as explicit standalone for debugging.

### Databases
- `build/game_templates.db` - space_bodies, hab_sites, mining_profiles, traits
- `build/savegame_YYYY-MM-DD.db` - campaign, gamestates (JSON blobs)

---

## Design Principles

### Robustness Principle (Postel's Law)
> *"Be conservative in what you do, be liberal in what you accept from others"*

- **Dates:** Accept YYYY-M-D, YYYY-MM-DD, DD/MM/YYYY → always output ISO 8601 internally
- **Paths:** Accept str or Path → always return Path objects
- **Env vars:** Accept missing optional vars gracefully → validate required vars explicitly
- **File search:** Match savegames with game format (YYYY-M-D, no padding) → store DB as ISO

### Other Principles
- One command = one package, self-contained
- No cross-package imports (except `core`)
- Absolute imports always: `from src.core.core import ...`
- Explicit over implicit: shell chaining, not compound commands
- Fail loudly with helpful messages

---

## Key Implementation Details

### Date Handling
`parse_flexible_date(date_str)` returns `(datetime, iso_string)`:
- `iso_string` = `YYYY-MM-DD` (with zero-padding) for DB filenames
- Savegame glob uses game format (YYYY-M-D, no padding) to match game files

### Path Resolution
`get_project_root()` → `Path(__file__).parent.parent.parent` (from `src/core/core.py`)

### Performance Tracking
All commands decorated with `@timed_command` log to `logs/performance.log`.

### Load: Malformed Templates
Game ships ~7 malformed JSON files. Load pipeline:
1. Try `json.load()` - fast path
2. On failure, try `_repair_json()` - strips `//` comments, trailing commas
3. Still fails → single warning at end (not one error per file)
4. Recovered files → logged at DEBUG only (`-vv`)

### Stage: Actor Context Assembly
`tias stage` reads from `resources/actors/<n>/`:
- `spec.toml` - identity, tier scopes, can/cannot discuss
- `background.txt` - character history
- `personality.txt` - voice and speech patterns (stub)
- `stage.txt` - actor-specific stage directions (stub)
- `examples_tier1/2/3.md` - example exchanges per tier (stub)

Tier source: `generated/tier_state.json` (fallback: Tier 1, future: `tias evaluate`)

---

## Actors (7 total)
- **Wale** - Covert/Asymmetric Operations
- **Valentina** - Intelligence & Counter-Intelligence
- **Lin** - Earth/Political Strategy
- **Jun-Ho** - Industrial & Energy Systems
- **Jonny** - Orbital Operations & Space Execution
- **Katya** - Military Doctrine & Ground Warfare
- **CODEX** - Data archivist, emotionless state evaluator

Actor data in `resources/actors/<n>/`: spec.toml, background.txt, personality.txt, stage.txt, examples_tier*.md, openers.csv, reactions.csv

---

## Technology Stack
- **Python:** 3.14 (3.11+ required)
- **LLM:** KoboldCpp, models from Mistral 7B Q4 (base) to Qwen 72B Q2 (ludicrous)
- **GPU:** AMD (Vulkan on Windows, CLBlast on Linux)
- **OS:** Windows (primary), Linux supported
- **DB:** SQLite (stdlib)
- **Package:** pip editable install (`pip install -e .`)

---

## Configuration (.env)
Key variables: `GAME_INSTALL_DIR`, `GAME_SAVES_DIR`, `KOBOLDCPP_DIR`, `KOBOLDCPP_MODEL_BASE`, `KOBOLDCPP_PORT`, `KOBOLDCPP_GPU_BACKEND`

---

## Testing
```bash
pytest                          # All tests
pytest tests/core/              # Core utilities
pytest tests/preset/            # Launch windows
pytest --cov=src                # With coverage
```

Test structure mirrors `src/` structure.

---

## What's Working
- All 9 commands: install, clean, load, validate, parse, stage, preset, play, perf
- Flexible date input, ISO internal format
- Malformed template recovery
- Editable install (`tias` command available globally)
- Stage: parse-if-stale + tier evaluation + context assembly in one command
- Tier evaluation: all T2/T3 conditions implemented (3 stubs: shipyard, orbital ring, mission success)
- Full documentation: README, DEVELOPER_GUIDE, docs/

## What's Next (see FEATURES.md)
- Wire preset to consume context_*.txt from stage
- Fill actor content files (personality.txt, stage.txt, examples_tier*.md)
- Context extraction extensions (faction data, councilor roster)
- Resolve stubs: shipyard module name, orbital ring habType, mission success rate

---

## Command Vocabulary (Theatre Metaphor)
- `tias load`    - Load game data into DB (load in the set)
- `tias parse`   - Parse savegame (read the script)
- `tias stage`   - Stage actors at current tier (stage the cast)
- `tias preset`  - Combine contexts + game state (preset the scene)
- `tias play`    - Launch KoboldCpp (curtain up)

---

## Session History
See `.ai/cache/` for detailed session summaries.

**Last Updated:** 2026-02-17 (Command renames: build→load, inject→preset, run→play)
