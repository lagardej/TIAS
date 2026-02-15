# Terra Invicta Advisory Council System

AI-powered advisory system for Terra Invicta featuring 6 specialist councilor advisors with CODEX strategic state evaluator. Uses 3-tier progression system that evolves with campaign complexity.

## Quick Start

```bash
# 1. Configure environment
cp scripts/.env.example scripts/.env
# Edit scripts/.env with your paths

# 2. Start KoboldCPP (see Installation below)

# 3. Run data injection at each Assignment Phase
python3 scripts/codex_inject.py /path/to/savegame.json.gz

# 4. Consult advisors via KoboldCPP chat interface
# Ask Lin about nations, Jonny about space, Chuck about covert ops, etc.
```

## System Overview

### The Advisory Council

**Six Domain Specialists:**
- **Lin Mei-hua** - Earth/Political Strategy (nations, control, diplomacy, federations)
- **Valentina Mendoza** - Intelligence/Counter-Intel (loyalty, infiltration, security)
- **Kim Jun-ho** - Industrial/Energy Systems (mining, power, research, MC)
- **Jonathan "Jonny" Pratt** - Orbital Operations (stations, fleets, space construction)
- **Chukwuemeka "Chuck" Okonkwo** - Covert/Asymmetric Ops (sabotage, assassination, wetwork)
- **Kateryna "Katya" Bondarenko** - Military Doctrine (combat, strategy, force deployment - Tier 2+)

**Strategic State Evaluator:**
- **CODEX** - Objective data analysis, tier evaluation, metrics tracking

### How It Works

**Preparation Phase Workflow:**
1. Pause game at Assignment Phase
2. Run `codex_inject.py` to sync game state
3. CODEX evaluates current situation and tier readiness
4. Random advisor opens meeting, CODEX provides status report
5. You ask advisors for strategic recommendations
6. 1-2 advisors respond (operational), others may comment (spectators)
7. Return to game and assign missions based on advice

**Meeting Dynamics:**
- Ask questions, advisors respond in character with expertise
- Spectators occasionally interject (Chuck 50%, Valentina 30%, others 15-20%)
- System remembers current + previous prep phase (not goldfish)
- User can override: "Ask Lin: should we invest in India?"

## Tier Progression System

**Tier 1 - Early Consolidation** (Game start)
- Focus: Nation control, basic space, bootstrap economy
- Advisors provide tactical, single-nation advice
- Katya mostly dormant (minimal militarization)

**Tier 2 - Industrial Expansion** (Unlock at 60% readiness)
- Focus: Mining, federations, MC management, defensive fleets
- Advisors expand to regional/bloc strategy
- Katya activates with military doctrine advice

**Tier 3 - Strategic Confrontation** (Unlock at 70% readiness)
- Focus: War economy, strategic warfare, global operations
- Advisors provide full strategic-scale planning
- All operational domains available

**CODEX evaluates readiness** based on:
- Mining operations (3+ functional mines)
- Shipyard construction
- Mission Control pressure
- Federation formation
- Economic resilience

## File Structure

```
~/TerraInvicta/
├── README.md                      # This file
├── REFERENCE.md                   # Quick reference (domains, thresholds)
│
├── src/                           # Human-editable source files
│   ├── actors/                    # Actor specifications + fluff
│   │   ├── actor_lin.md
│   │   ├── actor_lin_fluff.md
│   │   └── [12 more files]
│   ├── prompts/                   # TODO: Tier-specific prompts
│   ├── stage.md                   # Stage directions, meeting atmosphere
│   └── tiers.md                   # Tier system rules
│
├── build/                         # Build artifacts (gitignored)
│   └── [Optimized runtime JSON - future]
│
├── docs/                          # Documentation
│   ├── performance.md
│   ├── technical.md
│   └── workflow.md
│
├── generated/                     # Runtime data
│   ├── conversation_history.json
│   ├── tier_state.json
│   └── [filter/path files]
│
├── logs/                          # Runtime logs
│   └── advisory_council.log
│
├── scripts/                       # Automation scripts
│   ├── .env.example              # Configuration template
│   ├── .env                      # Your config (create this)
│   ├── codex_inject.py           # Main data sync script
│   └── [other scripts]
│
└── snapshots/                     # Archived game states
    └── [Snapshot files]
```

## Installation

### Prerequisites

**Hardware:**
- CPU: AMD Ryzen 7 9800X3D or equivalent
- RAM: 32GB
- GPU: AMD Radeon RX 9070 XT or equivalent (16GB+ VRAM)
- OS: Native Linux (Fedora recommended) for best performance

**Software:**
- Python 3.10+
- KoboldCPP
- Mistral 7B Q4 GGUF model (or similar)

### Setup Steps

```bash
# 1. Install system dependencies
sudo dnf install python3 python3-pip git vulkan-headers vulkan-loader-devel -y

# 2. Install KoboldCPP
cd ~
git clone https://github.com/LostRuins/koboldcpp
cd koboldcpp
make LLAMA_VULKAN=1

# 3. Download model to ~/koboldcpp/models/
# Get Mistral 7B Q4 from HuggingFace

# 4. Extract TerraInvicta advisory system
cd ~
unzip TerraInvicta_advisory.zip

# 5. Configure environment
cd TerraInvicta
cp scripts/.env.example scripts/.env
nano scripts/.env  # Edit with your paths

# 6. Start KoboldCPP
cd ~/koboldcpp
python3 koboldcpp.py \
  --model models/mistral-7b-q4.gguf \
  --port 5001 \
  --contextsize 8192 \
  --threads 8 \
  --usevulkan \
  --gpulayers 99
```

### Configuration

Edit `scripts/.env` with your paths:
```bash
# KoboldCPP
KOBOLDCPP_URL=http://localhost:5001
KOBOLDCPP_DIR=/home/user/koboldcpp

# Terra Invicta
GAME_SAVES_DIR=/home/user/.local/share/Pavonis Interactive/Terra Invicta

# Advisory System (relative paths OK)
DATA_DIR=./src
GENERATED_DIR=./generated
```

## Usage

### Basic Workflow

```bash
# 1. Start KoboldCPP (in separate terminal)
cd ~/koboldcpp
python3 koboldcpp.py --model models/mistral-7b-q4.gguf --port 5001 \
  --contextsize 8192 --usevulkan --gpulayers 99

# 2. Open chat interface
# Browser: http://localhost:5001

# 3. At each game Assignment Phase, sync data:
cd ~/TerraInvicta
python3 scripts/codex_inject.py ~/path/to/savegame.json.gz

# 4. In chat, advisors automatically present CODEX report

# 5. Ask strategic questions:
# "Lin, should we invest in India or Brazil?"
# "Jonny, when should we build our first station?"
# "Chuck, is this councilor worth assassinating?"

# 6. Return to game, assign missions based on advice
```

### Example Session

```
[Preparation Phase - 2026-03-15]

Chuck: "CODEX, how fucked are we today?" [cheerful]

CODEX REPORT:
Tier: 1
Tier 2 Readiness: 47%
Functional Mines: 2
Shipyard: Construction 67% complete
MC Utilization: 73%
Major Economies Controlled: 1 stable (USA)

You: Lin, should we focus on India or the EU next?

Lin: Based on March 15 intelligence, India shows higher stability (6.2 vs EU 
average 4.8) and faster GDP growth. Recommend establishing control in Delhi 
and Mumbai first. EU can wait until we have more influence capacity.

Chuck: "Just bribe them! Faster!" [cheerful suggestion]

Valentina: [Makes notes] "Verify India hasn't been infiltrated first."

You: Jonny, when should we start our first space station?

Jonny: Not yet. We have 2 mines operational but boost reserves are low. Wait 
until we have 3 mines and 500+ boost stockpiled. Current MC at 73% can handle 
the expansion. Target late March or early April.
```

### Advanced Features

**Force specific advisor:**
```
Ask Chuck: Is assassinating the Servant councilor in China viable?
```

**Query CODEX directly:**
```
CODEX, tier status
CODEX, what's our mining capacity?
```

**Tier unlock:**
When CODEX reports ≥60% readiness, you can manually unlock Tier 2 for expanded 
strategic advice.

## Performance

**Target:** <5 seconds per response
- Domain routing: ~0.05s
- Context loading: ~0.3s
- LLM generation: 2-3s (200-300 tokens)
- Formatting: ~0.1s

**Optimizations:**
- Native Linux (10-20% faster than WSL)
- Tier-filtered context (smaller = faster)
- Script-based CODEX evaluation (not LLM)
- Pre-written fluff variations (zero LLM cost)

## Documentation

- **REFERENCE.md** - Quick lookup (domains, probabilities, thresholds)
- **docs/technical.md** - Hardware specs, software stack, directory structure
- **docs/workflow.md** - Detailed operational workflow, memory system
- **docs/performance.md** - Performance targets, optimizations

## Troubleshooting

**KoboldCPP won't start:**
```bash
# Check if already running
curl http://localhost:5001/api/v1/model

# Kill existing instance
pkill -f koboldcpp

# Verify GPU
vulkaninfo | grep deviceName
```

**Scripts can't find paths:**
```bash
# Check .env configuration
cat scripts/.env

# Verify paths exist
ls $GAME_SAVES_DIR
ls $KOBOLDCPP_DIR
```

**No advisor response:**
- Check KoboldCPP is running (http://localhost:5001)
- Verify data injection completed successfully
- Check logs: `tail -f logs/advisory_council.log`

**Advisor personality seems off:**
- Verify correct model loaded (Mistral 7B or better)
- Check context window size (8192 minimum)
- Review src/actors/*.md files for expected behavior

## Tips

- **Generate snapshots** at key campaign moments for comparison
- **Monitor tier readiness** - CODEX reports progress toward unlocks
- **Use advisor overrides** when you need specific expertise
- **Check REFERENCE.md** for quick domain/threshold lookups
- **Larger models** (13B+) provide better personality consistency

## Known Limitations

- System works with Terra Invicta 1.0, 2026 scenario
- Advisors work with last Assignment Phase data (intelligence lag by design)
- Chuck has 50% reaction probability but won't react consecutively
- Tier unlocks are manual (player decides when ready)
- Build optimization (src/ → build/) not yet implemented

## Future Development

- [ ] Tier-specific prompt files (18 files: 6 actors × 3 tiers)
- [ ] Build optimization (markdown → JSON runtime format)
- [ ] Conversation example files
- [ ] Domain routing automation
- [ ] Performance monitoring dashboard

## Support

**For issues with:**
- Scripts: Check script headers for usage
- KoboldCPP: See https://github.com/LostRuins/koboldcpp
- Terra Invicta mechanics: Consult TI Wiki
- System design: Review docs/ folder

## License

Advisory system provided as-is for personal use with Terra Invicta.

---

**Quick Reference:** See REFERENCE.md for actor domains, spectator probabilities, and tier thresholds.
