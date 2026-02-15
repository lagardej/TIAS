# Workflow

## Game Integration Flow

### Three-Phase Cycle

**1. PREPARATION PHASE** (Outside game)
   - Pause game at Assignment Phase
   - Sync game state: `python terractl.py parse --date YYYY-M-D`
   - Generate context: `python terractl.py inject --date YYYY-M-D`
   - Launch LLM: `python terractl.py run --date YYYY-M-D`
   - Consult advisors via KoboldCpp chat
   - Advisors analyze state, recommend strategy
   - User decides final strategy

**2. ASSIGNMENT PHASE** (In-game)
   - Assign councilor missions per advisor recommendations
   - Confirm assignments
   - Advance to Resolution Phase

**3. RESOLUTION PHASE** (In-game)
   - Missions execute automatically
   - No LLM interaction during resolution
   - Observe outcomes

**4. NEXT ASSIGNMENT PHASE**
   - Return to Preparation Phase
   - Re-sync game state (new savegame)
   - Repeat cycle

## Data Sync Workflow

### Quick Sync (After Each Turn)

```bash
# 1. Save game with descriptive date
# Example: Resistsave00005_2027-8-14.gz

# 2. Parse new savegame
python terractl.py parse --date 2027-8-14

# 3. Update context
python terractl.py inject --date 2027-8-14

# 4. Context ready in generated/mistral_context.txt
# Load manually into KoboldCpp or use `run` command
```

### Full Rebuild (After Game Updates)

```bash
# 1. Clean all artifacts
python terractl.py clean

# 2. Rebuild templates from game files
python terractl.py build

# 3. Parse current savegame
python terractl.py parse --date YYYY-M-D

# 4. Generate fresh context
python terractl.py inject --date YYYY-M-D
```

## Typical Session

### Initial Setup

```bash
# One-time setup
cp .env.dist .env
# Edit .env with paths
python terractl.py build
```

### Per-Turn Workflow

```bash
# 1. Play game, reach Assignment Phase, save
# Filename: Resistsave00042_2028-3-7.gz

# 2. Sync state
python terractl.py parse --date 2028-3-7

# 3. Generate context  
python terractl.py inject --date 2028-3-7

# 4. Launch LLM
python terractl.py run --date 2028-3-7
# OR manually: KoboldCpp UI → load generated/mistral_context.txt

# 5. Chat with advisors
# Example prompts:
# - "Chuck, recommend covert ops priorities this turn"
# - "CODEX, evaluate our strategic position"
# - "Valentina, which faction is most vulnerable to infiltration?"

# 6. Execute strategy in-game

# 7. Advance to next turn, repeat
```

## Context Inspection

Context file location: `generated/mistral_context.txt`

**What's included:**
- Advisor list with domains
- Key hab sites (Luna, Mars) with resource ranges
- (Extensible: add factions, councilors, control points)

**Inspect before loading:**
```bash
cat generated/mistral_context.txt
# or
notepad generated/mistral_context.txt
```

Verify context contains expected game state before consulting advisors.

## Multiple Campaigns

### Managing Multiple Saves

```bash
# Campaign A (Resistance, 2027)
python terractl.py parse --date 2027-7-14
python terractl.py inject --date 2027-7-14

# Campaign B (Academy, 2028)  
python terractl.py parse --date 2028-2-3
python terractl.py inject --date 2028-2-3

# Databases persist:
# build/savegame_2027_7_14.db
# build/savegame_2028_2_3.db

# Context regenerates on each inject
```

### Switching Campaigns

Context file always reflects last `inject` command. To switch:

```bash
python terractl.py inject --date 2027-7-14  # Campaign A
python terractl.py run --date 2027-7-14

# Later...
python terractl.py inject --date 2028-2-3   # Campaign B
python terractl.py run --date 2028-2-3
```

## Debugging Workflow

### Verbose Logging

```bash
python terractl.py -v parse --date YYYY-M-D    # INFO level
python terractl.py -vv build                   # DEBUG level
```

Logs: `logs/terractl.log` (append mode, persists across runs)

### Verify Pipeline

```bash
# 1. Check templates DB
ls -lh build/game_templates.db
# Should be ~5MB

# 2. Check savegame DB
ls -lh build/savegame_*.db
# Should be ~13MB per savegame

# 3. Check context file
wc -l generated/mistral_context.txt
# Should be 50-100 lines (expandable)

# 4. Verify context content
head -n 20 generated/mistral_context.txt
```

### Common Issues

**Missing savegame:**
```
FileNotFoundError: No savegame found matching *_YYYY-M-D.gz
```
Fix: Check date format matches actual filename

**Outdated context:**
Symptom: Advisors reference old game state
Fix: Re-run `inject` after parsing new savegame

**Templates not building:**
Normal: 7/58 templates have invalid JSON in game files
Impact: None (advisory system uses 52 valid templates)

## Advanced: Custom Context

Edit `cmd_inject()` in `terractl.py` to add:
- Faction standings
- Councilor roster  
- Control point distribution
- Tech tree progress
- Resource stockpiles

Example addition:
```python
# In cmd_inject(), after hab sites:
cursor.execute('SELECT data FROM gamestates WHERE key = ?',
    ('PavonisInteractive.TerraInvicta.TIFactionState',))
factions = json.loads(cursor.fetchone()[0])

f.write("# FACTIONS\n")
for faction in factions:
    name = faction.get('displayName_key')
    cp = faction.get('controlPoints', 0)
    f.write(f"{name}: {cp} CP\n")
```

Re-inject to regenerate context with new data.
