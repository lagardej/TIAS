# Terra Invicta Advisory System - Feature Roadmap

This file tracks design ideas and optimizations to be implemented after core system is operational.

---

## Template Optimization

**Status:** Planned  
**Priority:** Medium  
**Complexity:** Medium

**Current State:**
- Templates read directly from game install (no copying)
- All fields loaded raw from JSON
- No filtering or optimization

**Goal:**
Optimize template data for advisor consumption while preserving operational information.

**Approach:**
1. **Profile actual advisor usage** - determine which fields each advisor domain actually uses
2. **Create per-template optimization rules** - filter unnecessary fields
3. **Denormalize cross-references** - embed related data to eliminate lookups
4. **Build optimized versions** - output to `build/templates/*.json`

**Example Optimizations:**

### TISpaceBodyTemplate.json
**Keep:**
- Identity: `dataName`, `displayName`, `objectType`
- Location: `barycenterName` (parent body)
- Orbital mechanics: ALL Kepler elements (needed for launch window calculations)
  - `semiMajorAxis_km`, `eccentricity`, `inclination_Deg`
  - `longAscendingNode_Deg`, `argPeriapsis_Deg`, `meanAnomalyAtEpoch_Deg`
  - `epoch_floatJYears`
- Physical: `mass_kg`, `equatorialRadius_km`, `density_gcm3`
- Operational: `orbits[]`, `habSites[]`, `maxHabSize`
- Environment: `atmosphere`, `irradiatedMultiplier`

**Remove:**
- Rendering: `modelResource`, `modelScale`, `symbolTexture`, `altModels`
- Display cosmetics: `angularDiameterMultiplier`, `rotationOffset_Deg`
- Internal calculations: `Hill Radius in km`, `Hill radius pass-fail`
- Duplicate fields: `friendlyName` (use `displayName`), `friendlyDiameter` (use `equatorialRadius_km * 2`)

**Denormalize:**
- `habSites[]`: Instead of array of strings `["LunaSite1", ...]`, embed full hab site data:
  ```json
  "habSites": [
    {
      "dataName": "LunaSite1",
      "displayName": "Mare Tranquillitatis",
      "miningProfile": {
        "dataName": "Volatiles_Rich",
        "resources": {"water": 8, "metals": 12, "nobles": 3},
        "extraction_rate": 1.2
      },
      "baseResources": {...},
      "coordinates": {...}
    }
  ]
  ```
- Eliminates need for separate HabSite and MiningProfile lookups

**Rationale:**
- Launch windows require precise orbital mechanics (discovered during design)
- Advisors need operational data, not rendering metadata
- Denormalization trades file size for query speed (no lookups)

### TIHabSiteTemplate.json
**Status:** May become obsolete if fully denormalized into SpaceBody

**If kept separate:**
- Keep: `dataName`, `displayName`, `body`, `miningProfile`, `baseResources`, `coordinates`
- Remove: Redundant fields already in parent SpaceBody

### TIMiningProfileTemplate.json
**Keep:**
- `dataName`, `displayName`
- Resource yields and extraction rates
- Efficiency modifiers

**Remove:**
- UI display metadata

### TITraitTemplate.json
**Keep:**
- `dataName`, `displayNameKey`, `descriptionKey`
- Mechanical effects (all stat modifiers)
- Conditions and restrictions

**Remove:**
- UI sorting metadata
- Flavor text not needed for decision-making

### TICouncilorTypeTemplate.json
**Keep:**
- `dataName`, `displayNameKey`
- `classChance[]` (trait compatibility)
- Stat base values

**Remove:**
- UI display preferences

**Implementation Notes:**
- Create optimization rules only after profiling real advisor queries
- Preserve ALL operational/scientific data (learned from orbital mechanics case)
- When in doubt, keep the field (disk space is cheap, missing data is expensive)
- Document why each field is kept/removed
- Version optimization rules with game version (1.0.0 template structure may differ from 1.1.0)

---

## Build Process Enhancements

**Status:** Planned  
**Priority:** Low  
**Complexity:** Low

**Ideas:**
- Incremental builds (only rebuild changed files)
- Parallel processing for large template sets
- Build validation (schema checking on output)
- Compression of build artifacts
- Source maps (map optimized data back to original template fields)

---

## Tier-Specific Prompts

**Status:** Planned  
**Priority:** High (blocks tier system)  
**Complexity:** Medium

**Current State:**
- Actor specs define tier 1/2/3 scope in markdown
- No actual prompt files created yet

**Goal:**
Create 18 prompt files (6 actors × 3 tiers) that enforce tier knowledge boundaries.

**Structure:**
```
src/prompts/
├── lin_tier1.txt
├── lin_tier2.txt
├── lin_tier3.txt
├── valentina_tier1.txt
└── ... (18 files total)
```

**Each prompt includes:**
- Actor personality and background
- Domain expertise
- Tier-specific knowledge scope (what they CAN discuss)
- Tier restrictions (what they CANNOT discuss)
- Response style and tone
- Example queries and responses

**Implementation:**
- Extract tier scopes from actor markdown specs
- Create templated prompts with variable tier knowledge
- Build process validates prompts against actor specs
- Runtime loads appropriate tier prompt based on current global tier

---

## Runtime Version Checking

**Status:** Planned  
**Priority:** Medium  
**Complexity:** Low

**Current State:**
- `build/.buildinfo` records game version
- No runtime validation yet

**Goal:**
Scripts check game version before using build artifacts.

**Implementation:**
```python
# In codex_inject.py and other runtime scripts:

def check_build_version(env):
    """Verify build artifacts match current game version"""
    buildinfo_path = Path(env['BUILD_DIR']) / '.buildinfo'
    
    if not buildinfo_path.exists():
        print("⚠ WARNING: No build artifacts found. Run 'python3 scripts/build.py' first.")
        return False
    
    with open(buildinfo_path) as f:
        buildinfo = json.load(f)
    
    build_version = buildinfo['game_version']
    current_version = env['GAME_VERSION']
    
    if build_version != current_version:
        print(f"⚠ WARNING: Build artifacts from game v{build_version}, current game is v{current_version}")
        print("  Template data may have changed. Recommend rebuilding:")
        print("  python3 scripts/build.py")
        response = input("Continue anyway? [y/N] ")
        return response.lower() == 'y'
    
    return True
```

**Features:**
- Detects version mismatch
- Warns user of potential issues
- Allows override (user decision)
- Suggests rebuild command

---

## Conversation Examples

**Status:** Planned  
**Priority:** Low  
**Complexity:** Low

**Current State:**
- Actor fluff has opener/reaction pools
- No full conversation examples

**Goal:**
Create example conversations showing:
- Actor personality in practice
- Tier 1 vs Tier 2 vs Tier 3 response differences
- Multi-advisor interactions
- Spectator behavior examples
- Error handling scenarios

**Location:** `src/actors/actor_*_examples.md` (separate from fluff)

**Purpose:**
- Development reference
- Prompt engineering validation
- User documentation
- Quality assurance

---

## Domain Routing Automation

**Status:** Planned  
**Priority:** High (blocks full automation)  
**Complexity:** Medium

**Current State:**
- Actor specs define domain keywords manually
- No automatic routing implementation

**Goal:**
Implement automatic advisor selection based on query content.

**Approach:**
1. Extract domain keywords from actor specs
2. Build keyword → advisor mapping
3. NLP-based query classification
4. Handle multi-domain queries (select 1-2 advisors)
5. User override: "Ask Lin: ..." forces specific advisor

**Implementation:**
```python
def route_query(query: str, actors: List[Dict]) -> List[str]:
    """
    Determine which advisors should respond to query
    
    Returns list of 1-2 advisor names
    """
    # Simple keyword matching initially
    # Can enhance with embeddings/classification later
    pass
```

---

## Performance Monitoring

**Status:** Planned  
**Priority:** Medium  
**Complexity:** Low

**Goal:**
Track actual system performance vs 5s target.

**Metrics:**
- Total response time (end-to-end)
- Component breakdown (routing, loading, LLM gen, formatting)
- Context window usage
- Token generation rate
- Memory consumption

**Implementation:**
- Logging decorators on key functions
- Performance dashboard (optional)
- Alerts when exceeding 5s budget

---

## CODEX Script-Based Evaluation

**Status:** Planned  
**Priority:** High (blocks tier unlocks)  
**Complexity:** Medium

**Current State:**
- CODEX role defined in actor specs
- No actual evaluation implementation

**Goal:**
Implement deterministic tier readiness calculation.

**Requirements:**
- Parse savegame for tier conditions (mines, shipyards, MC, federations)
- Calculate 2-of-5 unlock conditions
- Compute readiness percentage
- Output structured report (not LLM-generated)

**Implementation:**
- Extend `codex_inject.py` or create `codex_evaluate.py`
- Script-based calculation (~0.1s, not 1-2s LLM call)
- Format structured output template
- Save tier state to `generated/tier_state.json`

---

## Director/Validation System

**Status:** Idea  
**Priority:** Low  
**Complexity:** High

**Concept:**
Meta-layer that validates advisor responses for:
- In-character consistency
- Tier boundary compliance
- Factual accuracy vs game data
- Response quality

**Potential Implementation:**
- Second LLM pass after response generation
- Validates against actor specs and tier rules
- Flags out-of-character or incorrect responses
- Could use smaller/faster model for validation

**Open Questions:**
- Performance impact (adds latency)
- Value vs complexity trade-off
- Whether prompt engineering can achieve same quality without validation

---

## Notes

- Features listed in approximate priority order
- Complexity estimates: Low (1-2 days), Medium (3-5 days), High (1-2 weeks)
- Revisit and update as development progresses
- Some features may be abandoned if not needed
- New features discovered during development should be added here

**Last Updated:** 2026-02-14
