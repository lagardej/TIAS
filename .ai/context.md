# Terra Invicta Advisory System - Project Context

## Architecture Overview

AI-powered advisory system for Terra Invicta featuring 6 specialist councilor advisors with CODEX strategic state evaluator. Uses 3-tier progression system that evolves with campaign complexity.

**Core Concept:** Pause game at Assignment Phase → sync data → consult AI advisors → make decisions → assign missions → play Resolution Phase

## System Components

### Actors (6 Councilors + CODEX)
- **Lin Mei-hua** (55, Taiwan) - Earth/Political Strategy
- **Valentina Mendoza** (27-29, Colombia) - Intelligence/Counter-Intel
- **Kim Jun-ho** (47-49, North Korea defector) - Industrial/Energy Systems
- **Jonathan "Jonny" Pratt** (38-40, Pawnee/USA) - Orbital Operations
- **Chukwuemeka "Chuck" Okonkwo** (44-46, Nigeria) - Covert/Asymmetric Ops
- **Kateryna "Katya" Bondarenko** (27-29, Ukraine) - Military Doctrine (Tier 2+)
- **CODEX** - Strategic State Engine (data evaluator, not advisor)

### Tier System
- **Tier 1** - Early Consolidation (game start): tactical, single-nation focus
- **Tier 2** - Industrial Expansion (60% readiness): regional/bloc strategy
- **Tier 3** - Strategic Confrontation (70% readiness): global operations

**Unlock via:** 2-of-5 conditions (mines, shipyard, MC pressure, federation, resilience)

### Data Flow
```
Game Install (read-only)
    ↓ (templates referenced, not copied)
src/ (human edits)
    ↓ (build.py)
build/ (optimized runtime)
    ↓ (scripts load)
Savegame → codex_inject.py → KoboldCPP → User queries → Advisors respond
```

### Meeting Dynamics
- Random advisor opens, requests CODEX report
- CODEX posts tier status + metrics (script-generated, <0.1s)
- User asks questions
- 1-2 advisors operational (detailed response)
- Others spectators (occasional reactions)
  - Chuck: 50% (not consecutive)
  - Valentina: 30%
  - Others: 15-20%
- Memory: current + previous prep phase

## File Structure

```
~/TerraInvicta/
├── .env.dist → .env                # Config (at root, not in scripts/)
├── README.md, REFERENCE.md         # User docs
├── FEATURES.md                     # Future work tracking
│
├── .ai/                        # Project directives (this dir)
│   ├── instructions.md
│   ├── context.md
│   └── cache/                      # Session memory offload
│
├── src/                            # Human-editable source
│   ├── actors/
│   │   ├── actor_*.md             # Spec: background, traits, domains, tiers
│   │   └── actor_*_fluff.md       # Fluff: openers, reactions
│   ├── prompts/                   # TODO: 18 tier-specific prompts
│   ├── stage.md                   # Stage directions, meeting atmosphere
│   └── tiers.md                   # Tier unlock rules, context filtering
│
├── build/                          # Build artifacts (gitignored)
│   ├── actors/*.json              # Optimized from src/actors/*.md
│   ├── templates/*.json           # Future: optimized from game install
│   └── .buildinfo                 # Version tracking
│
├── docs/                           # Human documentation
│   ├── technical.md
│   ├── workflow.md
│   └── performance.md
│
├── generated/                      # Runtime data (gitignored)
│   ├── conversation_history.json
│   ├── tier_state.json
│   └── [filter files]
│
├── logs/                           # Runtime logs (gitignored)
├── scripts/                        # Python automation
│   ├── build.py                   # src/ + templates → build/
│   ├── codex_inject.py            # Sync savegame data
│   └── [other scripts]
│
└── snapshots/                      # Archived savegames
```

## Design Principles

### Read-Only Game Dependency
- Game install = dependency library (like node_modules)
- Never copy templates (version drift risk)
- Scripts read directly from `${GAME_INSTALL_DIR}/TerraInvicta_Data/StreamingAssets/`
- .buildinfo tracks game version
- Warn on version mismatch

### Build Pipeline
- **Input:** src/ (markdown) + game templates (JSON)
- **Process:** Filter, optimize, denormalize, structure
- **Output:** build/ (optimized JSON for runtime)
- **Trigger:** Manual (`python3 scripts/build.py`)
- **Benefit:** Human-readable source, machine-optimized runtime

### Performance Budget
- **Target:** <5s total response time
- **Breakdown:**
  - Domain routing: 0.05s
  - Context load: 0.3s
  - LLM generation: 2-3s
  - Formatting: 0.1s
- **Optimizations:**
  - Native Linux (10-20% faster than WSL)
  - Script-based CODEX (not LLM)
  - Tier-filtered context
  - Pre-written fluff (zero LLM cost)

### Version Tracking
- Game version in .env: `GAME_VERSION=1.0.0`
- Build records in .buildinfo:
  ```json
  {
    "build_timestamp": "...",
    "game_version": "1.0.0",
    "dependencies": {
      "templates_dir": "TerraInvicta_Data/StreamingAssets/Templates",
      "localization_dir": "TerraInvicta_Data/StreamingAssets/Localization/en"
    }
  }
  ```
- Runtime checks version, warns on mismatch

## Naming Conventions

### Files
- Actor specs: `actor_<name>.md` (e.g., `actor_lin.md`)
- Actor fluff: `actor_<name>_fluff.md`
- Build output: `<name>.json` (e.g., `lin.json`)
- Scripts: `lowercase_with_underscores.py`
- Docs: `lowercase.md`

### Environment Variables
- ALL_CAPS for .env entries
- Paths end in `_DIR` (e.g., `GAME_INSTALL_DIR`)
- Booleans: `ENABLE_*` prefix

### Python
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Private: `_leading_underscore`

## Common Patterns

### Error Handling
```python
try:
    # operation
except Exception as e:
    # Brief user message
    print(f"ERROR: {brief_message}")
    # Detailed log
    logger.error(f"Full context: {e}", exc_info=True)
```

### Path Resolution
```python
# Use .env, not hardcoded
env = load_env()
game_dir = Path(env['GAME_INSTALL_DIR'])
templates = game_dir / "TerraInvicta_Data/StreamingAssets/Templates"
```

### Version Checking
```python
# Compare versions
build_version = buildinfo['game_version']
current_version = env['GAME_VERSION']
if build_version != current_version:
    print(f"⚠ WARNING: Build v{build_version}, game v{current_version}")
    # Suggest rebuild
```

## Technology Stack

### Runtime
- **LLM:** Mistral 7B Q4 (via KoboldCPP)
- **Platform:** Native Linux (Fedora)
- **GPU:** AMD Radeon RX 9070 XT (Vulkan)
- **Context:** 8192 tokens
- **Interface:** KoboldCPP web UI (http://localhost:5001)

### Development
- **Language:** Python 3.10+
- **Build:** Custom build.py script
- **Config:** .env files
- **Docs:** Markdown
- **Version Control:** Git (assumed)

### Game Integration
- **Game:** Terra Invicta v1.0.0
- **Scenario:** 2026 start
- **Data:** JSON savegames (gzipped)
- **Templates:** Game install directory

## Key Decisions & Rationale

### Why markdown sources?
- Human-readable and editable
- Easy version control diffs
- Can build optimized JSON for runtime
- Best of both worlds

### Why not copy templates?
- Version drift (game updates, stale copies)
- Disk space waste
- Sync complexity
- Read-only dependency is cleaner

### Why global tier progression?
- Simpler than per-advisor tiers
- Matches campaign progression naturally
- All advisors unlock together = clear milestone

### Why script-based CODEX?
- Deterministic evaluation (no LLM randomness)
- Fast (<0.1s vs 1-2s)
- Saves LLM budget for advisor responses
- Tier math is simple logic, not inference

### Why preserve orbital mechanics?
- Needed for launch window calculations
- Learned requirement during design
- Example of why profiling before optimizing matters

## Unknown/TODO

- Which template fields each advisor domain actually needs (requires profiling)
- Exact savegame fields for tier evaluation
- Domain routing keyword effectiveness
- Actual LLM token usage per tier
- Real-world performance vs 5s target
- Whether 200-300 token responses are sufficient

## Session History

See `.ai/cache/` for detailed session summaries.

**Last Updated:** 2026-02-14 (Session 2)
