# TIAS Developer Reference Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Installation](#installation)
4. [Command Reference](#command-reference)
5. [Common Workflows](#common-workflows)
6. [Development](#development)
7. [Testing](#testing)
8. [Architecture](#architecture)

---

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd TerraInvicta
pip install -e .

# Setup
tias install

# Basic workflow
tias load
tias stage --date 2027-7-14
tias preset --date 2027-7-14
tias play --date 2027-7-14
```

---

## Project Structure

```
TerraInvicta/
├── src/                    # Source code (Python package)
│   ├── __main__.py        # Entry point (tias command)
│   ├── core/              # Core utilities
│   │   ├── core.py        # Logging, env, paths
│   │   └── date_utils.py  # Date parsing
│   ├── load/              # Load command
│   ├── clean/             # Clean command
│   ├── install/           # Install command
│   ├── parse/             # Parse command
│   ├── stage/             # Stage command
│   ├── preset/            # Preset command
│   │   └── launch_windows.py  # Launch window calculations
│   ├── play/              # Play command
│   ├── validate/          # Validate command
│   └── perf/              # Performance tracking
│       └── performance.py
├── resources/             # Game data (actors, prompts)
│   ├── actors/           # AI advisor definitions
│   └── prompts/          # LLM prompts
├── tests/                # Test suite
│   ├── core/             # Tests for src/core/
│   └── preset/           # Tests for src/preset/
├── build/                # Build output (gitignored)
├── generated/            # Generated context files
├── logs/                 # Application logs
├── docs/                 # Documentation
├── pyproject.toml        # Project metadata
└── .env                  # Configuration (gitignored)
```

**Key Principles:**
- Each command is a self-contained package
- Code in `src/` NEVER imports from sibling packages (except `core`)
- All imports use absolute paths: `from src.core.core import ...`
- Resources in `resources/`, not `src/`

---

## Installation

### First Time Setup

```bash
# Install in editable mode
pip install -e .

# Verify installation
tias --help

# Configure paths and models
tias install
```

### Development Dependencies

```bash
pip install -e ".[dev]"  # Includes pytest, pytest-cov
```

### Uninstall

```bash
pip uninstall tias
```

---

## Command Reference

### Core Commands

#### `tias install`
Interactive setup wizard. Auto-detects paths and creates `.env` file.

#### `tias clean`
Removes `build/` directory (templates and databases).

#### `tias load`
Imports game templates from Terra Invicta installation into SQLite.

```bash
tias load
```

**Output:**
- `build/actors/*.json` - Actor definitions
- `build/templates/*.json` - Game templates with localization
- `build/game_templates.db` - SQLite database

#### `tias validate`
Validates configuration and paths.

**Checks:** `.env` exists, game installation found, saves directory found, KoboldCpp found, model files exist.

#### `tias parse`
Parses savegame into SQLite database.

```bash
tias parse --date 2027-7-14
tias parse --date 2027-07-14      # Also works
tias parse --date 14/07/2027      # Also works
```

**Output:** `build/savegame_2027-07-14.db`

#### `tias stage`
Parses savegame (if needed), evaluates tier, assembles actor context files.

```bash
tias stage --date 2027-7-14
tias stage --date 2027-7-14 --force   # re-parse even if DB is current
```

**Input:** savegame .gz, `resources/actors/*/`, `resources/prompts/`
**Output:** `generated/tier_state.json`, `generated/context_*.txt` (one per actor + system + codex)

The `--force` flag bypasses the staleness check and always re-parses the savegame.

#### `tias preset`
Combines actor contexts and game state into final LLM context.

```bash
tias preset --date 2027-7-14
```

**Output:** `generated/mistral_context.txt`

#### `tias play`
Launches KoboldCpp with generated context.

```bash
tias play --date 2027-7-14
tias play --date 2027-7-14 --quality nuclear
```

**Quality tiers:** `base`, `max`, `nuclear`, `ridiculous`, `ludicrous`

#### `tias perf`
Shows performance statistics from `logs/performance.log`.

---

## Common Workflows

### Full Clean Load

```bash
tias clean && tias load
```

### Complete Pipeline

```bash
tias stage --date 2027-7-14 && \
tias preset --date 2027-7-14 && \
tias play --date 2027-7-14
```

### Quick Context Regeneration

```bash
# Skip parse if savegame hasn't changed
tias preset --date 2027-7-14 && tias play --date 2027-7-14
```

### Testing Different Quality Tiers

```bash
tias play --date 2027-7-14 --quality base
tias play --date 2027-7-14 --quality nuclear
tias play --date 2027-7-14 --quality ludicrous
```

### Validation Before Load

```bash
tias validate && tias load
```

---

## Design Philosophy

### Theatre Metaphor

The command vocabulary follows a theatre metaphor. When naming new commands, functions, or concepts, prefer theatre terminology where it fits naturally. Don't force it — clarity beats cleverness — but when a theatre term is equally clear, use it.

**Current vocabulary:**

| Command | Theatre meaning | What it does |
|---------|----------------|--------------|
| `tias load` | Load in (crew brings set into theatre) | Import game templates into SQLite |
| `tias parse` | Read the script | Parse savegame into SQLite |
| `tias stage` | Stage the cast | Assemble actor context files at current tier |
| `tias preset` | Preset the scene | Combine actor contexts + game state → LLM context |
| `tias play` | Curtain up | Launch KoboldCpp |

**Established terms in the codebase:**
- **Actor** - An advisor or CODEX (not "agent", "character", or "advisor" in code)
- **Stage directions** - Narrative asides and reactions (not "prompts" or "cues")
- **Spectator** - An advisor present but not the primary responder
- **Tier** - Campaign progression level (not "level", "rank", or "phase")
- **Opener** - Session-opening line (not "greeting" or "intro")
- **Reaction** - Short spectator comment (not "response" or "comment")

**Future commands to consider:** `tias rehearse` (dry-run validation?), `tias cast` (select active actors?), `tias cue` (trigger specific actor?)

---

### Design Principles

#### Robustness Principle (Postel's Law)
> *"Be conservative in what you do, be liberal in what you accept from others"*

| Aspect | Be liberal (accepting) | Be conservative (producing) |
|--------|----------------------|-----------------------------|
| **Dates** | Accept `YYYY-M-D`, `YYYY-MM-DD`, `DD/MM/YYYY` | Always output ISO 8601 internally |
| **Paths** | Accept `str` or `Path`, with or without trailing slash | Always output `Path` objects |
| **Env vars** | Accept missing optional vars gracefully | Always validate required vars explicitly |
| **File search** | Match savegames flexibly (glob patterns) | Write filenames with consistent format |

#### One Command, One Package

Each command is a self-contained package under `src/`. No command imports from another command package. The only shared code lives in `src/core/`. This keeps commands independently testable, independently replaceable, and prevents dependency tangles.

```
src/load/    ← knows nothing about src/preset/
src/preset/  ← knows nothing about src/play/
src/core/    ← the only shared ground
```

#### Explicit Over Implicit

Commands do one thing and exit. Compound behavior is expressed through shell chaining (`&&`), not hidden inside commands. This means the user always sees what ran, what succeeded, and what failed.

```bash
# ✅ Explicit: user sees every step
tias parse --date 2027-7-14 && tias stage && tias preset --date 2027-7-14

# ❌ Implicit: tias preset silently calls parse internally
tias preset --date 2027-7-14  # hidden behavior
```

*Exception:* `tias play` calls `tias preset` internally as a convenience. This is intentional and documented.

#### Fail Loudly

When something is wrong, say so clearly and stop. Don't silently skip, default, or work around bad input. A clear error now prevents a confusing result later.

```python
# ✅ Loud
if not templates_db.exists():
    logging.error("Templates DB missing. Run: tias load")
    return 1

# ❌ Silent
if not templates_db.exists():
    templates_db = None  # and then fail mysteriously later
```

#### Silence Is Not an Error

The inverse of failing loudly: if something is genuinely optional and missing, handle it gracefully without noise. Missing optional files, empty CSV files, skipped actors — these are normal states, not errors. Single summary warnings are better than one warning per item.

```python
# ✅ One summary, not one warning per file
if skipped:
    logging.warning(f"Skipped {len(skipped)} unrecoverable templates: {', '.join(skipped)}")
```

#### ISO 8601 Internally

Dates are accepted in multiple formats (Robustness Principle) but always normalized to ISO 8601 (`YYYY-MM-DD`) for internal use: DB filenames, log output, generated files. This makes files sortable, unambiguous, and standard.

```python
game_date, iso_date = parse_flexible_date(args.date)
db_path = build_dir / f"savegame_{iso_date}.db"  # always 2027-08-01, never 2027_8_1
```

Savegame *search* uses the game's own format (no zero-padding) to match filenames the game actually creates.

#### Game Data Is Read-Only

The Terra Invicta installation is a dependency, like a library. Never copy game files into the project. Always read directly from `GAME_INSTALL_DIR`. This prevents version drift and avoids stale copies after game updates.

```python
# ✅ Read from game install
templates_dir = Path(env['GAME_INSTALL_DIR']) / 'TerraInvicta_Data/StreamingAssets/Templates'

# ❌ Copied into project
templates_dir = project_root / 'data' / 'game_templates'
```

#### Absolute Imports Always

All imports use full paths from the package root. No relative imports. This makes it immediately clear where anything comes from, and avoids breakage when files move.

```python
# ✅ Absolute
from src.core.core import get_project_root
from src.perf.performance import timed_command

# ❌ Relative
from ..core.core import get_project_root
from core.core import get_project_root
```

---

### Adding a New Command

1. Create package: `src/newcommand/`
2. Add `__init__.py`
3. Create `command.py` with `cmd_newcommand(args)` function
4. Import in `src/__main__.py`
5. Add to argparse and dispatch dict

**Template:**

```python
# src/newcommand/command.py
"""
Newcommand - Brief description
"""

import logging
from src.core.core import get_project_root
from src.perf.performance import timed_command


@timed_command
def cmd_newcommand(args):
    """Command implementation"""
    project_root = get_project_root()

    # Your code here

    print("[OK] Command complete")
```

### Import Rules

```python
# ✅ CORRECT
from src.core.core import get_project_root
from src.perf.performance import timed_command

# ❌ WRONG
from core.core import get_project_root
```

### Path Handling

```python
from src.core.core import get_project_root

project_root = get_project_root()
resources = project_root / "resources"
build = project_root / "build"
```

### Logging

```python
import logging

logging.info("Informational message")
logging.warning("Warning message")
logging.error("Error message")
logging.debug("Debug message (only with -vv)")
```

**Verbosity levels:**
- `tias command` - Warnings only
- `tias -v command` - Info + warnings
- `tias -vv command` - Debug + info + warnings

---

## Testing

```bash
# All tests
pytest
pytest -v

# Specific module
pytest tests/core/
pytest tests/preset/

# Specific file
pytest tests/core/test_core.py
pytest tests/core/test_date_utils.py
pytest tests/preset/test_launch_windows.py

# With coverage
pytest --cov=src
pytest --cov=src --cov-report=html
```

---

## Architecture

### Package Philosophy

Each command package is **independent**:
- One command = one package
- No cross-package imports (except `core`)
- Self-contained functionality

### Pipeline

```
tias load    → game templates  → build/game_templates.db
tias stage   → savegame        → build/savegame_YYYY-MM-DD.db
             → tier evaluation → generated/tier_state.json
             → resources/      → generated/context_*.txt
tias preset  → context + game  → generated/mistral_context.txt
tias play    → launch KoboldCpp
```

`tias parse` remains available as an explicit standalone command for debugging.

### Performance Tracking

All commands decorated with `@timed_command` are automatically tracked:

```python
from src.perf.performance import timed_command

@timed_command
def cmd_mycommand(args):
    # Execution time logged to logs/performance.log
    pass
```

### Database Schema

**Templates DB:** `build/game_templates.db`
- `space_bodies` - Planets, moons, asteroids
- `hab_sites` - Habitation sites
- `mining_profiles` - Resource profiles
- `traits` - Character traits

**Savegame DB:** `build/savegame_YYYY-MM-DD.db`
- `campaign` - Campaign metadata
- `gamestates` - Full game state (JSON blobs)

---

## Configuration

### Environment Variables (.env)

```bash
# KoboldCpp
KOBOLDCPP_DIR=/path/to/koboldcpp
KOBOLDCPP_MODEL_BASE=/path/to/model.gguf
KOBOLDCPP_PORT=5001
KOBOLDCPP_GPU_BACKEND=vulkan
KOBOLDCPP_GPU_LAYERS=35

# Terra Invicta
GAME_INSTALL_DIR=/path/to/Terra Invicta
GAME_SAVES_DIR=/path/to/saves

# System
LOG_LEVEL=INFO
```

### Quality Tiers

| Tier | Model | Size | Use Case |
|------|-------|------|----------|
| base | mistral-7b-q4 | ~4GB | Fast iteration |
| max | mistral-7b-q6 | ~6GB | Better quality |
| nuclear | qwen2.5-14b-q4 | ~8GB | High quality |
| ridiculous | qwen2.5-32b-q4 | ~18GB | Production |
| ludicrous | qwen2.5-72b-q2 | ~40GB | Maximum quality |

---

## Performance Targets

| Command | Target | Description |
|---------|--------|-------------|
| load    | <1.0s  | Template + DB creation |
| parse   | <0.5s  | Savegame decompression |
| stage   | <0.1s  | Context assembly |
| preset  | <0.02s | Context generation |
| validate| <0.5s  | Path checking |

View actual performance: `tias perf`
