# Terra Invicta Advisory System

LLM-powered advisory system for Terra Invicta campaign gameplay. Provides domain-specific guidance through 6 specialized councilor advisors plus CODEX state evaluator.

## Overview

**Advisors (7 total):**
- **Chuck** - Covert/Asymmetric Operations
- **Valentina** - Intelligence & Counter-Intelligence  
- **Lin** - Earth/Political Strategy
- **Jun-Ho** - Industrial & Energy Systems
- **Jonny** - Orbital Operations & Space Execution
- **Katya** - Military Doctrine & Ground Warfare
- **CODEX** - Data archivist, emotionless state evaluator

**Tier System:**
- Tier 1 (0-60%): Basic operations, individual targets
- Tier 2 (60-70%): Strategic operations, faction-level
- Tier 3 (70%+): Global operations, civilization-scale

## Quick Start

### Prerequisites
- Python 3.11+
- Terra Invicta v1.0.29 (Steam/GOG)
- KoboldCpp + Mistral 7B Q4 model (local LLM)
- AMD GPU: ROCm drivers (Linux) or Vulkan support (Windows/Linux)

### Setup

1. **Clone repository:**
```bash
git clone <repo-url>
cd TerraInvicta
```

2. **Configure environment:**
```bash
# Interactive setup (recommended)
python terractl.py install

# Manual setup (alternative)
# Linux: cp .env.linux.dist .env
# Windows: cp .env.win.dist .env
# Then edit .env with your paths
```

3. **Build game data:**
```bash
python terractl.py build
```

4. **Parse savegame:**
```bash
python terractl.py parse --date 2027-7-14
```

5. **Generate LLM context:**
```bash
python terractl.py inject --date 2027-7-14
```

6. **Launch KoboldCpp:**
```bash
python terractl.py run --date 2027-7-14
# Manually load data/mistral_context.txt into KoboldCpp UI
```

## Commands

### `terractl.py` - Unified control script

```bash
# Interactive setup with auto-detection
python terractl.py install

# Clean build artifacts (removes entire build/ directory)
python terractl.py clean

# Build templates database from game files
python terractl.py build

# Parse savegame to database
python terractl.py parse --date YYYY-M-D

# Generate optimized LLM context
python terractl.py inject --date YYYY-M-D

# Launch KoboldCpp with auto-configured GPU settings
python terractl.py run --date 2027-7-14

# Increase verbosity
python terractl.py -v build      # INFO level
python terractl.py -vv build     # DEBUG level
```

## Architecture

### Data Pipeline

```
Game Templates (read-only)          Savegame .gz (compressed JSON)
        ↓                                    ↓
   Build Process                       Parse Process
        ↓                                    ↓
game_templates.db (SQLite)          savegame_YYYY_M_D.db (SQLite)
        ↓                                    ↓
        └────────────────┬───────────────────┘
                         ↓
                  Inject Process
                         ↓
           generated/mistral_context.txt
                         ↓
              KoboldCpp system prompt
```

### File Structure

```
TerraInvicta/
├── terractl.py          # Single unified control script (800 lines)
├── .env                 # Local configuration (gitignored)
├── .env.linux.dist      # Linux configuration template
├── .env.win.dist        # Windows configuration template
├── README.md            # This file
├── src/
│   └── actors/          # Actor definitions
│       ├── chuck/
│       │   ├── spec.toml        # Identity, domain, tiers
│       │   ├── background.txt   # Prose description
│       │   ├── openers.csv      # CODEX greeting variations
│       │   └── reactions.csv    # Spectator reactions
│       └── ... (7 actors total)
├── build/               # Generated artifacts (gitignored, recreated by build)
│   ├── game_templates.db        # Static game data (52 templates)
│   ├── savegame_YYYY_M_D.db     # Campaign state snapshots
│   ├── actors/*.json            # Compiled actor specs
│   └── templates/*.json         # Templates with merged localization
├── generated/           # Runtime generated files (gitignored)
│   └── mistral_context.txt      # LLM system prompt (inspectable)
└── logs/
    └── terractl.log             # Build/parse/inject logs
```

### Data Sources

1. **Game Templates** (static reference data)
   - Source: `GAME_INSTALL_DIR/TerraInvicta_Data/StreamingAssets/`
   - Format: 58 JSON templates + 71 `.en` localization files
   - Output: `build/game_templates.db` (SQLite, ~5MB)
   - Contains: Celestial bodies, hab sites, mining profiles, traits, tech tree

2. **Savegames** (dynamic campaign state)
   - Source: `GAME_SAVES_DIR/*_YYYY-M-D.gz`
   - Format: ~13MB compressed JSON (~150MB uncompressed)
   - Output: `build/savegame_YYYY_M_D.db` (SQLite, ~13MB)
   - Contains: All game state (62 gamestate keys as JSON blobs)

3. **Actor Specs** (simulation configuration)
   - Source: `src/actors/*/`
   - Format: TOML (spec) + CSV (dialogue) + TXT (background)
   - Output: `build/actors/*.json` (7 files)
   - Defines: Advisor personalities, domains, tier-specific scopes

## Database Schema

### game_templates.db

**Tables:**
- `space_bodies` - Celestial objects (68 bodies: planets, moons, asteroids)
- `hab_sites` - Habitable locations (629 sites with resource profiles)
- `mining_profiles` - Resource generation ranges (mean, width, min for each resource)
- `traits` - Councilor traits (166 traits with localized descriptions)

**Example Queries:**
```sql
-- Lunar sites with water resources
SELECT h.displayName, p.water_mean, p.water_min, p.water_width
FROM hab_sites h
JOIN mining_profiles p ON h.miningProfile = p.dataName
WHERE h.body = 'Luna' AND p.water_mean > 0;

-- Mars sites ranked by metals
SELECT displayName, metals 
FROM hab_sites 
WHERE body = 'Mars' 
ORDER BY metals DESC;
```

### savegame_YYYY_M_D.db

**Tables:**
- `campaign` - Metadata (key-value pairs)
- `gamestates` - All game state (key = class name, data = JSON blob)

**Available gamestate keys:**
- `PavonisInteractive.TerraInvicta.TICouncilorState` (154 councilors)
- `PavonisInteractive.TerraInvicta.TIFactionState` (8 factions)
- `PavonisInteractive.TerraInvicta.TIControlPoint` (524 control points)
- 59 other gamestate types

**Example Query:**
```sql
-- Extract all councilors
SELECT json_extract(data, '$') as councilors
FROM gamestates 
WHERE key = 'PavonisInteractive.TerraInvicta.TICouncilorState';
```

## Hardware Optimization

**Reference specs:** AMD Ryzen 7 9800X3D (8-core, 4.7GHz) + AMD RX 9070 XT + 32GB RAM

**GPU Backend Selection:**
- **Linux + AMD:** `KOBOLDCPP_GPU_BACKEND=clblast` (ROCm, best performance)
- **Windows + AMD:** `KOBOLDCPP_GPU_BACKEND=vulkan` (cross-platform)
- **NVIDIA:** `KOBOLDCPP_GPU_BACKEND=cublas` (CUDA)

**Recommended Settings (.env):**
```bash
KOBOLDCPP_GPU_BACKEND=clblast    # or vulkan for Windows
KOBOLDCPP_GPU_LAYERS=35          # Offload most layers to GPU
KOBOLDCPP_CONTEXT_SIZE=16384     # 16K context (32GB RAM)
KOBOLDCPP_THREADS=8              # Match CPU cores
```

**Expected Performance:**
- ROCm (clblast): ~45 tokens/s
- Vulkan: ~35-40 tokens/s
- CPU only: ~8-10 tokens/s

## Development

### Adding New Actor

1. Create directory: `src/actors/newactor/`
2. Add files (use `src/actors/_template/` as guide):
   - `spec.toml` - Identity, domain, tier scopes
   - `background.txt` - Prose character description
   - `openers.csv` - CODEX greeting variations (30 rows recommended)
   - `reactions.csv` - Spectator reactions with categories
3. Rebuild: 
```bash
python terractl.py clean
python terractl.py build
```

### Modifying Context Generation

Edit `cmd_inject()` function in `terractl.py` (line ~460) to customize data extraction.

Current extraction includes:
- Actor list with domains
- Hab sites for Luna/Mars with resource ranges
- (Extend with: factions, councilors, control points, etc.)

**Why file-based context?**
- Inspectable for debugging
- Version controllable
- Shareable across runs
- Manual tweaking/testing possible
- ~10ms overhead negligible vs debuggability

### Extending Database Schema

Add tables in `create_templates_db()` or `cmd_parse()` functions in `terractl.py`.

## Performance Metrics

**Build Pipeline:**
- Clean: <0.1s
- Build: ~0.5s (52 templates + 7 actors + DB creation)
- Parse: ~0.4s (decompress 13MB + insert 62 keys)
- Inject: ~0.01s (query DBs + write context)
- **Total: <1s for full pipeline**

**File Sizes:**
- `game_templates.db`: ~5MB
- `savegame_*.db`: ~13MB
- `mistral_context.txt`: ~4KB (expandable)
- Total build artifacts: ~20MB per savegame

## Troubleshooting

**Build errors for 7 templates:**
Expected behavior. Game files contain invalid JSON (trailing commas):
- TIGlobalConfig, TIMapGroupVisualizerTemplate, TIMetaTemplate
- TIPlayerTemplate, TISpaceFleetTemplate, TISpaceShipTemplate
- TITimeEventTemplate

**Result:** 52/58 templates build successfully. Missing templates don't affect advisory system.

**Savegame not found:**
```
FileNotFoundError: No savegame found matching *_YYYY-M-D.gz
```
**Fix:**
1. Check `GAME_SAVES_DIR` path in `.env`
2. Common locations:
   - Linux: `~/.local/share/Pavonis Interactive/Terra Invicta/Saves`
   - Windows: `C:\Users\YourName\Documents\My Games\TerraInvicta\Saves`
3. Verify date format matches savegame filename

**Windows console encoding errors:**
System uses ASCII `[OK]` markers instead of Unicode checkmarks for full Windows compatibility.

**KoboldCpp GPU not detected:**
- AMD users: Install ROCm drivers (Linux) or ensure Vulkan support
- Verify GPU backend setting matches your hardware
- Check logs for GPU initialization messages

## Known Limitations

- Read-only access to game files (no save modification)
- Savegame must be manually synchronized (run `parse` after each game session)
- Context injection into KoboldCpp is manual (paste `data/mistral_context.txt`)
- Tier progression not yet automated (CODEX evaluation pending)

## Roadmap

- [ ] Automated tier detection via CODEX evaluation
- [ ] Real-time savegame monitoring
- [ ] Tier-specific prompt templates
- [ ] Domain-specific routing logic
- [ ] Extended context extraction (factions, councilors, tech tree)
- [ ] Web interface for context inspection

## License

MIT License

## Credits

Built for Terra Invicta by Pavonis Interactive

**Advisory System Development:**
- Design & Implementation: Anthropic Claude (assisted)
- Game Data Analysis: Terra Invicta community
- Performance Optimization: User feedback

**Special Thanks:**
- Pavonis Interactive for Terra Invicta
- KoboldCpp project for local LLM support
- Mistral AI for Mistral 7B model
