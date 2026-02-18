# Workflow Guide

## Game Integration Flow

### Three-Phase Cycle

**1. PREPARATION PHASE** (Outside game)
   - Pause game at Assignment Phase
   - Sync game state: `tias parse --date YYYY-M-D`
   - Stage actor contexts: `tias stage`
   - Generate context: `tias preset --date YYYY-M-D`
   - Launch LLM: `tias play --date YYYY-M-D`
   - Consult advisors via KoboldCpp chat
   - User decides final strategy

**2. ASSIGNMENT PHASE** (In-game)
   - Assign councilor missions per advisor recommendations
   - Advance to Resolution Phase

**3. RESOLUTION PHASE** (In-game)
   - Missions execute automatically
   - No LLM interaction during resolution

**4. NEXT ASSIGNMENT PHASE**
   - Return to Preparation Phase, re-sync, repeat

## Command Chaining

### Basic Pipeline

```bash
# Full pipeline
tias parse --date 2027-7-14 && \
tias stage && \
tias preset --date 2027-7-14 && \
tias play --date 2027-7-14
```

### Conditional Execution

```bash
# Only continue if previous command succeeds
tias clean && tias load && echo "Load successful"

# Run even if previous fails (PowerShell)
tias clean; tias load

# Stop on first error (Bash)
set -e
tias clean
tias load
tias parse --date 2027-7-14
```

### Common Chains

```bash
# Clean reload
tias clean && tias load

# Quick context update (skip parse, skip stage if actors unchanged)
tias preset --date 2027-7-14 && tias play --date 2027-7-14

# Validation + load
tias validate && tias load

# Full pipeline with quality tier
tias parse --date 2027-7-14 && \
tias stage && \
tias preset --date 2027-7-14 && \
tias play --date 2027-7-14 --quality nuclear
```

## Typical Session

### Initial Setup (One Time)

```bash
pip install -e .
tias install
tias load
```

### Per-Turn Workflow

```bash
# 1. Play game, reach Assignment Phase, save
# Filename: Resistsave00042_2028-3-7.gz

# 2. Full pipeline
tias parse --date 2028-3-7 && \
tias stage && \
tias preset --date 2028-3-7 && \
tias play --date 2028-3-7

# 3. Chat with advisors in KoboldCpp
# - "Wale, recommend covert ops priorities this turn"
# - "CODEX, evaluate our strategic position"
# - "Valentina, which faction is most vulnerable to infiltration?"

# 4. Execute strategy in-game, advance to next turn, repeat
```

## Date Format Flexibility

```bash
tias parse --date 2027-7-14     # YYYY-M-D
tias parse --date 2027-07-14    # YYYY-MM-DD
tias parse --date 14/07/2027    # DD/MM/YYYY
# All equivalent
```

## Context Management

### Inspecting Context

```bash
cat generated/mistral_context.txt
wc -l generated/mistral_context.txt
head -n 20 generated/mistral_context.txt
```

**What's included:** Advisor list, hab sites (Luna/Mars), launch windows (Mars, NEAs).

### Regenerating Context

```bash
# Quick regeneration (same savegame, actors unchanged)
tias preset --date 2027-7-14

# After new savegame
tias parse --date 2027-7-15 && tias preset --date 2027-7-15

# After changing actor content files
tias stage && tias preset --date 2027-7-14
```

## Multiple Campaigns

```bash
# Campaign A (Resistance, 2027)
tias parse --date 2027-7-14 && tias preset --date 2027-7-14

# Campaign B (Academy, 2028)
tias parse --date 2028-2-3 && tias preset --date 2028-2-3

# Switch to Campaign A
tias preset --date 2027-7-14 && tias play --date 2027-7-14
```

Databases persist: `build/savegame_2027-07-14.db`, `build/savegame_2028-02-03.db`

## Quality Tier Selection

```bash
tias play --date 2027-7-14 --quality base       # Fast (Mistral 7B Q4)
tias play --date 2027-7-14 --quality nuclear    # Better (Qwen 14B Q4)
tias play --date 2027-7-14 --quality ludicrous  # Maximum (Qwen 72B Q2)
tias play --date 2027-7-14                      # Default from .env
```

## Debugging Workflow

```bash
# INFO level logging
tias -v parse --date 2027-7-14

# DEBUG level logging
tias -vv load

# Verify pipeline
ls -lh build/game_templates.db    # ~5MB
ls -lh build/savegame_*.db        # ~13MB per savegame
wc -l generated/mistral_context.txt
tias validate
tias perf
```

Logs: `logs/terractl.log`

### Common Issues

**Missing savegame:** Verify date format matches actual savegame filename.

**Outdated context:** Re-run `tias preset` after parsing new savegame.

**Import errors:** `pip uninstall tias && pip install -e .`

## Scripting

### Bash

```bash
#!/bin/bash
# update-context.sh
DATE="$1"
[ -z "$DATE" ] && echo "Usage: $0 YYYY-M-D" && exit 1

tias parse --date "$DATE" && \
tias stage && \
tias preset --date "$DATE" && \
tias play --date "$DATE"
```

### PowerShell

```powershell
# update-context.ps1
param($Date)
if (-not $Date) { Write-Error "Usage: .\update-context.ps1 YYYY-M-D"; exit 1 }

tias parse --date $Date
if ($LASTEXITCODE -eq 0) {
    tias stage
    tias preset --date $Date
    if ($LASTEXITCODE -eq 0) { tias play --date $Date }
}
```

## Best Practices

1. **Always chain commands** - Use `&&` to stop on errors
2. **Save frequently** - Create savegames at every Assignment Phase
3. **Consistent naming** - Use date format in savegame names
4. **Check logs** - Review `logs/terractl.log` after errors
5. **Clean loads** - Use `tias clean && tias load` after game updates

---

For complete command reference, see [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)
