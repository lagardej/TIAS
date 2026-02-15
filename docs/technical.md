# TECHNICAL

## TECHNICAL SPECIFICATIONS

### Hardware Requirements

**Minimum Specifications:**
- CPU: AMD Ryzen 7 9800X3D (or equivalent)
- RAM: 32GB
- GPU: AMD Radeon RX 9070 XT (or equivalent with 16GB+ VRAM)
- Storage: 50GB free space (SSD recommended)
- OS: Native Linux (Fedora recommended)

**Why Native Linux:**
- No WSL overhead/translation layer
- Better Vulkan driver support (AMDGPU vs Windows drivers)
- Lower system resource usage
- Direct hardware access
- Better GPU scheduling
- Expected 10-20% performance gain over WSL

### Software Stack

**Core Components:**
- **KoboldCPP:** LLM inference server
- **Model:** Mistral 7B Q4 quantization
- **Acceleration:** Vulkan (full GPU offload - 99 layers)
- **Context Size:** 8192 tokens
- **Threads:** 8-12 (adjust based on workload)

**Python Environment:**
- Python 3.10+
- Required packages: see requirements.txt
- Virtual environment recommended

**Game Integration:**
- Terra Invicta v1.0
- 2026 scenario start
- Savegame format: JSON (gzipped)

### Directory Structure

```
~/terra_invicta/
├── scripts/                        # Python automation
│   ├── codex_map_candidates.py     # Discover data paths
│   ├── codex_validator.py          # Validate filters
│   ├── codex_inject.py             # Extract and inject data
│   ├── codex_manager.py            # Manage workflow
│   └── explore_savegame.py         # Examine savegame structure
│
├── data/                           # Model reference data
│   ├── actors/                     # Per-actor specifications
│   │   ├── actor_lin.md
│   │   ├── actor_valentina.md
│   │   ├── actor_jun-ho.md
│   │   ├── actor_jonny.md
│   │   ├── actor_chuck.md
│   │   ├── actor_katya.md
│   │   └── actor_codex.md
│   │
│   ├── actors/                     # Example conversations (TODO)
│   │   ├── actor_lin_examples.md
│   │   ├── actor_valentina_examples.md
│   │   ├── actor_jun-ho_examples.md
│   │   ├── actor_jonny_examples.md
│   │   ├── actor_chuck_examples.md
│   │   ├── actor_katya_examples.md
│   │   └── actor_codex_examples.md
│   │
│   ├── prompts/                    # Tier-specific prompts (TODO)
│   │   ├── lin_tier1.txt
│   │   ├── lin_tier2.txt
│   │   ├── lin_tier3.txt
│   │   └── [18 files total - 6 actors × 3 tiers]
│   │
│   ├── ruleset.txt                 # AI advisor rules
│   └── requirements_example.txt    # Data requirements template
│
├── generated/                      # Mutable runtime data
│   ├── candidate_paths.txt         # Discovered data paths
│   ├── final_filters.txt           # Active data filters
│   ├── tier_state.json             # Current tier per advisor
│   └── conversation_history.json   # Last 2 prep phases
│
├── logs/                           # Runtime logs
│   └── advisory_council.log        # System and error logs
│
└── snapshots/                      # Game state archives
    ├── snapshot_YYYY-MM-DD.json.gz # Monthly snapshots
    └── delta_YYYY-MM-DD.txt        # Change deltas
```

### Script Usage

**Discovery Workflow:**
```bash
# 1. Discover available data in savegame
python3 scripts/codex_map_candidates.py savegame.json.gz

# 2. Review candidates, create filter file
nano generated/final_filters.txt

# 3. Validate filters
python3 scripts/codex_validator.py savegame.json.gz

# 4. Inject data (triggers prep phase)
python3 scripts/codex_inject.py savegame.json.gz
```

**Automated Workflow:**
```bash
# Full automated injection
python3 scripts/codex_manager.py savegame.json.gz
```

**Exploration:**
```bash
# Examine savegame structure
python3 scripts/explore_savegame.py savegame.json.gz
```

### Runtime Constraints

**Performance Budget:** <5 seconds per advisor response

**Token Limits:**
- Context window: 8192 tokens maximum
- Response length: 200-300 tokens target
- Conversation history: Last 2 preparation phases only

**Memory Management:**
- Clear history older than 2 prep phases
- Compress old snapshots
- Archive logs monthly

---

