# Terra Invicta Advisory System - Feature Roadmap

This file tracks design ideas and features to be implemented.

**Last Updated:** 2026-02-17

---

## Implementation Status

### ✅ Completed

**Unified Command System (tias)**
- Python package with editable install (`pip install -e .`)
- 9 commands: install, clean, load, validate, parse, stage, preset, play, perf
- Full pipeline: `tias load && tias parse && tias stage && tias preset && tias play`
- SQLite-based data pipeline (game_templates.db + savegame_*.db)
- Flexible date input (YYYY-M-D, YYYY-MM-DD, DD/MM/YYYY)
- Performance tracking with `@timed_command`

**Data Pipeline**
- Game templates → SQLite with localization merge
- Malformed template auto-recovery (_repair_json)
- Savegames → SQLite (dated snapshots)
- Context generation → generated/mistral_context.txt

**Stage Command**
- Per-actor context assembly at current tier
- Reads tier from generated/tier_state.json (fallback: Tier 1)
- Output: generated/context_*.txt (one per actor + system + codex)

---

## Tier-Specific Prompts

**Status:** In Progress
**Priority:** High (blocks tier system)
**Complexity:** Medium

**Current State:**
- Actor specs define tier 1/2/3 scope in TOML
- Stub content files created for all 7 actors (personality.txt, stage.txt, examples_tier*.md)
- `tias stage` assembles context files but content is TODO

**Goal:**
Fill personality.txt, stage.txt, and examples_tier*.md for all actors.

**What's needed per actor:**
- `personality.txt` - Voice, speech patterns, behavioral traits
- `stage.txt` - Actor-specific stage directions and spectator reactions
- `examples_tier1.md` - 3-5 example exchanges at Tier 1 + boundary enforcement
- `examples_tier2.md` - 3-5 example exchanges at Tier 2 + boundary enforcement
- `examples_tier3.md` - 3-5 example exchanges at Tier 3

**Also needed:**
- `resources/prompts/system.txt` - Global council rules and tone
- `resources/prompts/codex_eval.txt` - CODEX session-opening report template

---

## CODEX Script-Based Tier Evaluation

**Status:** Planned
**Priority:** High (blocks tier progression)
**Complexity:** Medium

**Decision:** Evaluation is an integral part of staging, not a separate command.
`tias stage` will evaluate tier internally before assembling actor contexts.
See `docs/savegame_structure.md` for confirmed JSON key mappings.

**Goal:**
Implement tier evaluation inside `tias stage` - reads savegame DB, calculates
tier readiness, writes `tier_state.json`, then assembles actor contexts.

**Output:** `generated/tier_state.json` (consumed by `tias stage`)

**Tier Unlock Conditions:**

Tier 2 (60-70%): Meet 2 of 5 conditions
1. Operative on Luna or Mars mine
2. Operative on Earth shipyard
3. 10+ MC
4. Control 3+ space stations
5. Member of 3+ nation federation

Tier 3 (70%+): Meet 3 of 6 conditions
1. Control orbital ring or space elevator
2. Fleet in Jupiter system or beyond
3. 25+ MC
4. Control 10+ habs
5. Federation of 5+ major powers
6. Councilor-level mission success rate >80%

---

## Consolidate parse into stage

**Status:** Planned
**Priority:** Medium
**Complexity:** Low

**Current situation:**
`tias stage` needs the savegame DB to evaluate tier readiness, which means
`tias parse --date DATE` must always be run before `tias stage --date DATE`.
They are always called together — there is no use case for running stage
without first having parsed a savegame.

**Goal:**
Merge `tias parse` into `tias stage`. Stage takes `--date DATE`, parses the
savegame internally if the DB is missing or older than the savegame file,
then evaluates tier, then assembles contexts.

**New pipeline:**
```
tias load                          # once, after game install/update
tias stage --date DATE             # parse + evaluate + assemble (was 3 commands)
tias preset --date DATE            # combine contexts + game state
tias play --date DATE              # curtain up
```

**Design notes:**
- `tias parse` command remains as a standalone for debugging/explicit use
- Stage should skip re-parse if savegame DB already exists and is newer than the .gz file
- `--force` flag to bypass staleness check if needed
- The `src/parse/` package stays; stage calls its logic internally

---

## Domain Routing Automation

**Status:** Planned
**Priority:** Medium
**Complexity:** Medium

**Goal:** Automatic advisor selection based on query content.

Phase 1: Keyword matching against `domain_keywords` in spec.toml
Phase 2: Embedding-based semantic similarity (future)

User override: `@wale [question]` forces Wale to respond.

---

## Context Extraction Extensions

**Status:** Planned
**Priority:** Medium
**Complexity:** Low-Medium

**Goal:** Extend `tias preset` with richer game state data.

**Additional data to extract from savegame_*.db:**
- Faction standings and control points
- Councilor roster with traits/stats/missions
- Space fleets with composition and location
- Nation control and federation membership
- Current research progress
- Resource stockpiles
- Active missions

Keep total context under 16K tokens.

---

## Auto-Correction of Malformed Game Templates

**Status:** Done (implemented in tias load)

Terra Invicta ships ~7 malformed JSON files. The load command now:
1. Tries `json.load()` first
2. Falls back to `_repair_json()` (strips `//` comments, trailing commas)
3. Truly unrecoverable files → single WARNING at end (not one error per file)

---

## V2 Future Expansion

### Tier System Expansion
**Priority:** Low (3 tiers sufficient for current scope)
**Complexity:** Medium

Current system: 3 tiers, thresholds at 60% (T2) and 70% (T3).
Tier count is hardcoded in tier_check logic and spec.toml error message keys.
If expanded: add tier_N_scope/can/cannot blocks to spec.toml, add error_out_of_tier_N,
and update tier_check confidence thresholds (currently: correct tier = full, one below = hedged, two below = hard block).

---

## Advanced Features (Lower Priority)

### Engine-Agnostic Backend
**Priority:** Low
**Complexity:** Low

The chat loop already speaks OpenAI-compatible API — KoboldCpp, LM Studio, Ollama, llama.cpp server all work unchanged.
What's KoboldCpp-specific: subprocess launch, `KOBOLDCPP_*` env vars, readiness check URL.

Implementation: add `BACKEND_URL` env var (default `http://localhost:5001`). If set to LM Studio (`http://localhost:1234`) or any other server, chat loop works unchanged. Subprocess launch becomes optional — skip if server already running externally.

Env var rename `KOBOLDCPP_*` → `LLM_*` or `BACKEND_*` is the main work. Low risk, low value until a second backend is actually needed.

---

### Real-Time Savegame Monitoring
Watch saves directory, auto-parse on new .gz file. Complexity: Medium.

### Web Interface
Browser-based chat with advisors, visual context inspection. Complexity: High.

### Multi-Campaign Management
Track and switch between multiple campaigns. Complexity: Medium.

### Voice Integration
TTS/STT for immersive RP. Complexity: High.

### Validation & Quality Assurance
Meta-layer validating advisor responses for tier compliance, domain accuracy.
Recommendation: Start with prompt engineering (free), add rule-based checks if needed.

### Conversation Examples
Document example conversations per tier in `docs/examples/`. Complexity: Low.

---

## Notes

- Complexity estimates: Low (1-2 days), Medium (3-5 days), High (1-2 weeks)
- Tier system (content + evaluation) is critical path
- Context extraction can be incremental
- Quality assurance via prompting preferred over validation overhead
