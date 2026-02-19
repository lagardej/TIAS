# TECHNICAL SPECIFICATIONS

## Hardware Requirements

**Minimum Specifications:**
- CPU: AMD Ryzen 7 9800X3D (or equivalent)
- RAM: 32GB
- GPU: AMD Radeon RX 9070 XT (or equivalent with 16GB+ VRAM)
- Storage: 50GB free space (SSD recommended)
- OS: Native Linux (Fedora recommended) or Windows 10/11

**Why Native Linux (Recommended):**
- No WSL overhead/translation layer
- Better Vulkan driver support (AMDGPU vs Windows drivers)
- Lower system resource usage
- Direct hardware access
- Better GPU scheduling
- Expected 10-20% performance gain over WSL

## Software Stack

**Core Components:**
- **KoboldCpp:** LLM inference server
- **Models:** Mistral 7B Q4 (base) to Qwen 72B Q2 (ludicrous)
- **Acceleration:** Vulkan or CLBlast (full GPU offload)
- **Context Size:** 8192-16384 tokens
- **Threads:** 8-12 (adjust based on workload)

**Python Environment:**
- Python 3.11+ (required)
- Package management: pip with editable install
- Virtual environment: Optional but recommended

**Game Integration:**
- Terra Invicta v1.0.29+
- Savegame format: JSON (gzipped)
- Multiple date formats supported

## Project Structure

```
TIAS/
├── src/                           # Python package (installed)
│   ├── __main__.py               # Entry point (tias command)
│   ├── core/                     # Core utilities
│   │   ├── core.py              # Logging, env, paths
│   │   └── date_utils.py        # Date parsing
│   ├── build/                    # Build command
│   │   └── command.py
│   ├── clean/                    # Clean command
│   │   └── command.py
│   ├── install/                  # Install command
│   │   └── command.py
│   ├── parse/                    # Parse command
│   │   └── command.py
│   ├── inject/                   # Inject command
│   │   ├── command.py
│   │   └── launch_windows.py
│   ├── run/                      # Run command
│   │   └── command.py
│   ├── validate/                 # Validate command
│   │   └── command.py
│   └── perf/                     # Performance tracking
│       ├── command.py
│       └── performance.py
│
├── resources/                     # Game data (not installed)
│   ├── actors/                   # AI advisor definitions
│   │   ├── wale/               # Covert operations
│   │   ├── valentina/           # Intelligence
│   │   ├── lin/                 # Political strategy
│   │   ├── jun-ho/              # Industrial systems
│   │   ├── jonny/               # Orbital operations
│   │   ├── katya/               # Military doctrine
│   │   ├── codex/               # State evaluator
│   │   └── _template/           # Actor template
│   ├── prompts/                 # LLM prompts (future)
│   ├── stage.md                 # Tier progression
│   └── tiers.md                 # Tier definitions
│
├── tests/                        # Test suite
│   ├── test_launch_windows.py   # Launch window tests
│   ├── test_core.py             # Core utility tests
│   └── __init__.py
│
├── build/                        # Build output (gitignored)
│   ├── actors/                  # Built actor JSON
│   ├── templates/               # Game templates
│   ├── game_templates.db        # SQLite database
│   └── savegame_*.db            # Parsed savegames
│
├── generated/                    # Generated files (gitignored)
│   └── mistral_context.txt      # LLM context
│
├── logs/                         # Runtime logs (gitignored)
│   ├── terractl.log             # Application log
│   └── performance.log          # Performance tracking
│
├── docs/                         # Documentation
│   ├── technical.md             # This file
│   ├── workflow.md              # User workflows
│   └── performance.md           # Performance targets
│
├── setup.py                      # Package setup
├── pyproject.toml               # Project metadata
├── .env                         # Configuration (gitignored)
└── README.md                    # Main documentation
```

## Installation

```bash
# Clone repository
git clone <repo-url>
cd TIAS

# Install in editable mode
pip install -e .

# Verify
tias --help
```

**Editable install means:**
- Source code changes take effect immediately
- No need to reinstall after edits
- Package available system-wide via `tias` command

## Command Architecture

**Design Philosophy:**
- One command = one package
- Each command is self-contained
- No cross-package dependencies (except `core`)
- All imports use absolute paths: `from src.package.module import ...`

**Entry Point Flow:**
```
tias command [args]
    ↓
src/__main__.py (argparse)
    ↓
src/COMMAND/command.py (cmd_COMMAND function)
    ↓
src/core/* (shared utilities)
```

**Performance Tracking:**
All commands decorated with `@timed_command` log to `logs/performance.log`

## Database Schema

### Templates Database (`build/game_templates.db`)

```sql
-- Celestial bodies
CREATE TABLE space_bodies (
    dataName TEXT PRIMARY KEY,
    displayName TEXT,
    objectType TEXT,
    parent TEXT,
    mass_kg TEXT,
    radius_km REAL
);

-- Habitation sites
CREATE TABLE hab_sites (
    dataName TEXT PRIMARY KEY,
    displayName TEXT,
    body TEXT,
    miningProfile TEXT,
    water INT,
    metals INT,
    nobles INT,
    fissiles INT
);

-- Resource profiles
CREATE TABLE mining_profiles (
    dataName TEXT PRIMARY KEY,
    displayName TEXT,
    water_mean REAL, water_width REAL, water_min REAL,
    metals_mean REAL, metals_width REAL, metals_min REAL,
    nobles_mean REAL, nobles_width REAL, nobles_min REAL,
    fissiles_mean REAL, fissiles_width REAL, fissiles_min REAL
);

-- Character traits
CREATE TABLE traits (
    dataName TEXT PRIMARY KEY,
    displayName TEXT,
    description TEXT
);
```

### Savegame Database (`build/savegame_YYYY_M_D.db`)

```sql
-- Campaign metadata
CREATE TABLE campaign (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Full game state (JSON blobs)
CREATE TABLE gamestates (
    key TEXT PRIMARY KEY,
    data TEXT
);
```

## Data Flow

```
Terra Invicta Installation
    ↓ (tias build)
build/templates/*.json (localized)
    ↓
build/game_templates.db (SQLite)

Savegame File
    ↓ (tias parse)
build/savegame_*.db (SQLite)

Templates DB + Savegame DB
    ↓ (tias inject)
generated/mistral_context.txt

Context File
    ↓ (tias run)
KoboldCpp (LLM server)
```

## Performance Targets

| Command | Target | Typical | Description |
|---------|--------|---------|-------------|
| build | <1.0s | ~0.8s | Template + DB creation |
| parse | <0.5s | ~0.3s | Savegame decompression + SQL |
| inject | <0.02s | ~0.01s | Context generation |
| validate | <0.5s | ~0.2s | Path checking |
| clean | <0.1s | ~0.05s | Directory removal |

View actual performance: `tias perf`

## Launch Window Calculations

**Mars Transfer Windows:**
- Synodic period: 780 days
- Penalty calculation: Square-root based formula
- Accuracy: <1% error vs in-game values
- Verified against: 2026-02-01, 2027-08-01, optimal windows

**Near-Earth Asteroids:**
- Sisyphus: 592 days synodic period
- Hephaistos: 533 days synodic period
- Currently: Next window date only (no penalty yet)

**Algorithm:**
```python
days_from_optimal = abs(current_date - optimal_date)
penalty = sqrt(days_from_optimal / synodic_period) * 100
```

## Actor System

Each actor has:
- `spec.toml` - Metadata (name, domain, display name)
- `background.txt` - Character background
- `openers.csv` - Conversation starters
- `reactions.csv` - Response patterns

**Build process:**
1. Read TOML spec
2. Load background text
3. Parse CSV files
4. Combine into JSON
5. Output to `build/actors/*.json`

## Quality Tiers

| Tier | Model | Size | Layers | Use Case |
|------|-------|------|--------|----------|
| base | Mistral 7B Q4 | ~4GB | 32 | Fast iteration |
| max | Mistral 7B Q6 | ~6GB | 32 | Better quality |
| nuclear | Qwen 14B Q4 | ~8GB | 40 | High quality |
| ridiculous | Qwen 32B Q4 | ~18GB | 64 | Production |
| ludicrous | Qwen 72B Q2 | ~40GB | 80 | Maximum quality |

**GPU Offload:**
- Vulkan: Works on all GPUs (AMD/NVIDIA)
- CLBlast: OpenCL-based (ROCm for AMD)
- Full offload: All layers on GPU

## Configuration

### Environment Variables (`.env`)

```bash
# KoboldCpp paths
KOBOLDCPP_DIR=/path/to/koboldcpp
KOBOLDCPP_MODEL_BASE=/path/to/mistral-7b-q4.gguf
KOBOLDCPP_MODEL_MAX=/path/to/mistral-7b-q6.gguf
KOBOLDCPP_MODEL_NUCLEAR=/path/to/qwen2.5-14b-q4.gguf
KOBOLDCPP_MODEL_RIDICULOUS=/path/to/qwen2.5-32b-q4.gguf
KOBOLDCPP_MODEL_LUDICROUS=/path/to/qwen2.5-72b-q2.gguf

# KoboldCpp settings
KOBOLDCPP_PORT=5001
KOBOLDCPP_GPU_BACKEND=vulkan
KOBOLDCPP_GPU_LAYERS=35
KOBOLDCPP_CONTEXT_SIZE=16384
KOBOLDCPP_THREADS=8

# Terra Invicta paths
GAME_INSTALL_DIR=/path/to/Terra Invicta
GAME_SAVES_DIR=/path/to/saves

# System
LOG_LEVEL=INFO
CURRENT_TIER=1
```

### Automatic Detection

`tias install` auto-detects:
- Game installation (common Steam/GOG locations)
- Savegame directory (platform-specific)
- GPU backend (Vulkan for Windows, CLBlast for Linux)

## Development

### Adding Commands

1. Create package: `src/newcommand/`
2. Add `__init__.py`
3. Create `command.py`:
```python
from src.core.core import get_project_root
from src.perf.performance import timed_command

@timed_command
def cmd_newcommand(args):
    project_root = get_project_root()
    # Implementation
    print("[OK] Done")
```
4. Update `src/__main__.py`:
   - Import function
   - Add subparser
   - Add to dispatch dict

### Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific file
pytest tests/test_launch_windows.py
```

### Import Rules

**Always use absolute imports:**
```python
# ✅ Correct
from src.core.core import get_project_root

# ❌ Wrong
from core.core import get_project_root
```

## Troubleshooting

### Import Errors
```bash
pip uninstall tias
pip install -e .
```

### Path Issues
Always use `get_project_root()`:
```python
from src.core.core import get_project_root
root = get_project_root()  # Correct project root
```

### Performance Issues
Check logs: `logs/performance.log`
Run: `tias perf`

## Future Enhancements

- [ ] NEA transfer window penalty calculations
- [ ] Tier-specific prompt injection
- [ ] Conversation history tracking
- [ ] Multi-advisor coordination
- [ ] Web UI for easier access
- [ ] API endpoint for external tools

---

For complete command reference, see [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)
