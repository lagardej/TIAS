# TIAS Framework Design: Campaign-Agnostic Architecture

## Vision

TIAS should be a **framework for Terra Invicta advisory systems**, not a hardcoded Resistance campaign tool. Different campaigns (Resistance, Exodus, Academy, etc.) should be able to plug in their own advisors, personalities, and tones without modifying core code.

## Separation of Concerns

### Framework (Universal - Core Code)
**Location:** `src/`  
**Scope:** Campaign-agnostic game mechanics and orchestration  

```
src/
├── core/           # Shared utilities (paths, dates, logging)
├── parse/          # Savegame parsing (game format is universal)
├── stage/          # Tier evaluation + context assembly (generic)
├── preset/         # Domain extraction (game state is universal)
└── play/           # LLM orchestration (prompt structure is generic)
```

**What the framework provides:**
- Parse any Terra Invicta savegame
- Evaluate tier conditions (unlock logic is game-defined)
- Load actor specs dynamically from `resources/actors/`
- Assemble contexts using generic template
- Extract game state into domain files
- Launch LLM with assembled context

**What the framework does NOT do:**
- Define specific advisors (that's content)
- Hardcode personality traits (that's content)
- Assume faction identity (that's content)

### Content Packs (Campaign-Specific)
**Location:** `resources/` (V1) or `campaigns/<name>/` (future)  
**Scope:** Advisor personalities, faction tone, campaign flavor  

```
resources/          # V1: Resistance campaign (hardcoded location)
├── actors/
│   ├── wale/      # Individual advisor definition
│   │   ├── spec.toml
│   │   ├── background.txt
│   │   ├── personality.txt
│   │   └── examples_tier1.md
│   ├── jonny/
│   └── lin/
└── prompts/
    ├── system.txt      # Campaign-wide tone and rules
    └── codex_eval.txt  # Campaign-specific evaluation template

Future campaigns/ (V2+):
campaigns/
├── resistance/     # Resistance campaign content
│   ├── campaign.toml
│   ├── actors/
│   └── prompts/
├── exodus/         # Different advisors, different tone
│   ├── campaign.toml
│   └── ...
└── academy/        # Different advisors, different tone
    └── ...
```

**What content packs define:**
- Who the advisors are (names, roles, domains)
- How they talk (personality, speech patterns)
- What they know (domain expertise, tier scopes)
- Campaign tone (cynical Resistance vs idealistic Exodus)

## V1 Implementation Strategy

### Phase 1: Hardcoded Resistance (Current)
**Status:** What we're building now  
**Goal:** Prove the concept works end-to-end  

```
Resources structure:
resources/
├── actors/
│   ├── wale/      # Resistance advisors (hardcoded)
│   ├── jonny/
│   └── lin/
└── prompts/
    └── system.txt  # Resistance tone (hardcoded)
```

**Framework assumptions (acceptable for V1):**
- Actors always in `resources/actors/`
- System prompt always at `resources/prompts/system.txt`
- One campaign per installation

**What we validate:**
- ✅ Actor loading from file structure (not Python code)
- ✅ Tier evaluation works with any actor set
- ✅ Domain routing uses `spec.toml` keywords
- ✅ Context assembly is template-driven
- ✅ LLM integration works

### Phase 2: Campaign Abstraction (V2)
**Status:** Design documented, not implemented  
**Goal:** Support multiple campaigns without reinstalling  

```
New structure:
campaigns/
├── resistance/
│   ├── campaign.toml       # Campaign metadata
│   │   [campaign]
│   │   name = "The Resistance"
│   │   faction = "Resistance"
│   │   tone = "cynical_professionalism"
│   │   
│   │   [[actors]]
│   │   id = "wale"
│   │   required = true
│   │
│   ├── actors/
│   │   └── wale/
│   └── prompts/
└── exodus/
    ├── campaign.toml       # Different advisors
    │   [campaign]
    │   name = "Project Exodus"
    │   faction = "Exodus"
    │   tone = "optimistic_pragmatism"
    │
    ├── actors/
    │   └── different_people/
    └── prompts/
```

**Framework enhancements:**
```bash
# Campaign management
tias campaign list
tias campaign select resistance
tias campaign create exodus

# Pipeline now campaign-aware
tias stage --campaign resistance --date 2027-8-1
tias preset --campaign resistance --date 2027-8-1
```

**Output structure:**
```
generated/
├── resistance/
│   └── 2027-08-01/
└── exodus/
    └── 2027-08-01/
```

## Actor Specification (Campaign-Agnostic)

The `spec.toml` format is already campaign-agnostic. No changes needed:

```toml
# Any campaign can define an actor this way
[actor]
name = "wale"
display_name = "Wale 'Ankledeep' Oluwaseun"
domain_primary = "Covert/Asymmetric Operations"
domain_keywords = ["assassination", "sabotage", "infiltration", "wetwork"]

[tier_1]
scope = "Targeted sabotage, assassination ROI, low-escalation disruption"
can_discuss = "Individual target operations, simple sabotage"
cannot_discuss = "Strategic faction weakening campaigns"

# Tier 2/3 scopes...
```

**What makes this universal:**
- No faction references
- No hardcoded campaign assumptions
- Pure domain expertise definition
- Reusable across any Terra Invicta campaign

**Campaign-specific flavor:**
- Goes in `personality.txt` and `examples_tier1.md`
- Example: Resistance Wale is cynical mercenary
- Example: Exodus Wale could be idealistic volunteer
- Same domain (covert ops), different personality

## Tier Evaluation (Campaign-Agnostic)

Tier unlock conditions are **game mechanics**, not campaign choices:

```python
# Already campaign-agnostic - no changes needed
def evaluate_tier(db_path: Path) -> dict:
    # Find player faction (whoever the human controls)
    player_faction_key, pf = _find_player_faction(db_path)
    
    # Evaluate unlock conditions (same for any faction)
    mc_capacity = pf.get('baseIncomes_year', {}).get('MissionControl', 0)
    player_habs = [h for h in all_habs if h['faction'] == player_faction_key]
    
    tier2_unlocked = (mc_capacity >= 10 and len(player_habs) >= 2)
    # ... etc
```

**Why this works for any campaign:**
- No hardcoded faction names
- Uses player_faction_key dynamically
- Unlock conditions are Terra Invicta rules (universal)

## Domain Extraction (Campaign-Agnostic)

Game state extraction is **pure data**, no campaign flavor:

```python
# Already campaign-agnostic - no changes needed
def write_earth(db_path: Path, out: Path):
    nations = load_nations(db_path)
    player_cps = find_player_control_points(db_path)
    
    # Output facts (works for any faction)
    lines.append("Nation,GDP,Unrest,Control Points")
    for nation in nations:
        lines.append(f"{nation.name},{nation.gdp},{nation.unrest}")
```

**Why this works for any campaign:**
- No assumptions about player goals
- No editorializing ("good" vs "bad" nations)
- Pure observation of game state

## LLM Orchestration (Campaign-Agnostic)

The orchestrator structure is **template-driven**:

```
Current assembly (V1):
[system prompt from resources/prompts/system.txt]
[actor contexts from resources/actors/*/]
[game state from preset extractors]

Future assembly (V2):
[system prompt from campaigns/{name}/prompts/system.txt]
[actor contexts from campaigns/{name}/actors/*/]
[game state from preset extractors]
```

**What stays the same:**
- Load system prompt from file (path changes, structure doesn't)
- Load actor specs from directory scan (location changes, format doesn't)
- Concatenate in order: system → actors → game state

## Migration Path: V1 → V2

### Step 1: V1 Validates the Pattern
Build Resistance campaign in current structure:
- Prove actor loading works
- Prove tier evaluation is faction-agnostic
- Prove domain extraction has no campaign bias
- Document what worked / what didn't

### Step 2: Refactor for Multi-Campaign (V2)
```bash
# One-time migration script
python scripts/migrate_to_campaigns.py

# Moves:
resources/ → campaigns/resistance/
# Creates:
campaigns/resistance/campaign.toml
```

### Step 3: Add Second Campaign
```bash
# User creates new campaign
tias campaign create exodus

# Framework scaffolds:
campaigns/exodus/
├── campaign.toml
├── actors/
│   └── _example/   # Template actor
└── prompts/
    └── system.txt  # Template prompt

# User fills in their advisors
```

### Step 4: SQLite Backend (V2 AGENTIC)
Both campaign formats supported:
- File-based (simple, portable)
- DB-based (optimized, live memory)

User chooses per-campaign in `campaign.toml`:
```toml
[storage]
mode = "files"  # or "sqlite" for V2 AGENTIC
```

## Validation Criteria

### V1 Success = Framework Proof
- [ ] Actor loading: no hardcoded names in `stage/command.py`
- [ ] Tier eval: uses player_faction_key, not "Resistance"
- [ ] Extraction: pure data, no campaign editorializing
- [ ] Assembly: template-driven, not faction-specific logic

### V2 Success = Multi-Campaign Works
- [ ] User can `tias campaign create` without coding
- [ ] Switching campaigns changes available actors
- [ ] Tier evaluation works identically for all campaigns
- [ ] Generated contexts reflect campaign-specific tone
- [ ] No cross-contamination between campaigns

## Documentation Deliverables

### For V1 (Now)
- [x] This design doc (`FRAMEWORK_DESIGN.md`)
- [ ] `docs/creating_campaigns.md` (how to make new campaigns in V2)
- [ ] Comments in code marking "Campaign-agnostic - do not hardcode"

### For V2 (Later)
- [ ] `campaigns/resistance/README.md` (example campaign walkthrough)
- [ ] `campaigns/_template/` (scaffold for new campaigns)
- [ ] `scripts/migrate_to_campaigns.py` (V1 → V2 migration)

## Open Questions

1. **Campaign metadata location (V2):**
   - Option A: `campaigns/resistance/campaign.toml`
   - Option B: `campaigns.toml` at root with all campaign definitions
   - **Decision:** A (keeps campaigns self-contained)

2. **Actor ID conflicts:**
   - What if Resistance and Exodus both have a "Wale"?
   - **Decision:** Namespaced by campaign (`resistance_wale` vs `exodus_wale`)

3. **Shared actors across campaigns:**
   - Should some actors be reusable (e.g., CODEX)?
   - **Decision:** Defer to V2, copy for V1

4. **Campaign-specific game state extraction:**
   - Should extraction logic be pluggable?
   - **Decision:** No, game state is universal, interpretation happens in prompts

## References

- `V1_TO_V2_ROADMAP.md` - Migration timeline
- `AGENTIC.txt` - V2 architecture proposals
- `resources/actors/wale/spec.toml` - Example campaign-agnostic actor spec

---

**Status:** Design documented, V1 implements as "Resistance campaign template"  
**Next Review:** After V1 validation, before V2 implementation  
**Last Updated:** 2026-02-18
