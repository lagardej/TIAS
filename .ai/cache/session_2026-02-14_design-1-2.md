# Session Cache - Design Sessions 1-2

**Date:** 2026-02-14  
**Topics:** Initial system design, actor specifications, file structure, version tracking

## Session 1: Foundation

### Actors Defined
Created complete specifications for 6 councilors + CODEX:
- Lin Mei-hua (55, Taiwan) - Earth/Political, aggressive diplomat, wants to liberate mainland China
- Valentina Mendoza (27-29, Colombia) - Intelligence, paranoid investigative journalist, vindicated conspiracy theorist
- Kim Jun-ho (47-49, NK defector) - Industrial/Energy, pacifist physicist, family left behind
- Jonathan "Jonny" Pratt (38-40, Pawnee/USA) - Orbital Ops, SEAL→MD→astronaut, reconnecting with heritage
- Chuck Okonkwo (44-46, Nigeria) - Covert Ops, mercenary with Pollyanna trait (cheerful cynicism)
- Kateryna "Katya" Bondarenko (27-29, Ukraine) - Military (Tier 2+), active duty officer, combat veteran
- CODEX - Strategic State Engine, emotionless data evaluator

### Tier System
- 3 tiers (Early Consolidation → Industrial Expansion → Strategic Confrontation)
- Unlock at 60% (Tier 2), 70% (Tier 3) readiness
- 2-of-5 conditions: mines, shipyard, MC, federation, economic resilience
- CODEX evaluates via script (not LLM), reports percentage
- Global progression (all advisors unlock together)

### File Structure Evolution
Initial: `data/` with everything mixed
Interim: Separate `data/` and `docs/`
Final: `src/` (source) + `build/` (artifacts) pattern

### Meeting Mechanics
- Preparation Phase: pause game, sync data, consult advisors
- Random advisor opens, CODEX reports status
- 1-2 operational advisors, others spectators
- Spectator probabilities: Chuck 50% (not consecutive), Valentina 30%, others 15-20%
- Memory: current + previous prep phase

### Performance Design
- Target: <5s response time
- Native Linux for 10-20% gain
- Script-based CODEX saves 1-2s
- Tier-filtered context
- Pre-written fluff (zero LLM cost)

## Session 2: Configuration & Templates

### .env Migration
Moved from `scripts/.env.example` to `.env.dist` at project root
- Standard software pattern
- Added GAME_VERSION tracking
- Documented template paths (Templates/, Localization/en)

### Game as Read-Only Dependency
Key decision: Never copy templates
- Read directly from `${GAME_INSTALL_DIR}/TerraInvicta_Data/StreamingAssets/`
- Prevents version drift
- .buildinfo tracks game version
- Runtime warns on mismatch

### Template Optimization Discovery
Discussed filtering SpaceBodyTemplate fields:
- Initially: Remove orbital mechanics (rendering data)
- **Correction:** Preserve orbital mechanics (needed for launch windows)
- Lesson: Profile before optimizing, keep operational/scientific data

Template structure insight:
- Templates/ - game data templates
- Localization/en - English language files (note: capital L on Linux)

### Build System Design
Created `scripts/build.py`:
- Input: src/*.md + game templates
- Process: Parse, optimize, denormalize
- Output: build/*.json + .buildinfo
- Future: Per-template optimization rules after profiling

### Chuck Personality Rebalance
Problem: Fluff showed bitter cynicism
Trait: Pollyanna = cheerful outlook
Solution: Rewrote openers/reactions as cheerful cynicism
- Professional mode: Serious when operational (covert ops domain)
- Off-duty mode: "CODEX, how fucked are we today?" [cheerful tone]
- Han Solo energy, not bitter mercenary

### Documentation Updates
- README.md: Complete rewrite (removed TERRA/ASTRA, added 6 advisors, current workflow)
- REFERENCE.md: Quick lookup at root
- FEATURES.md: Living doc for brainstorming and future work
- .ai/: Project directives and session cache

## Key Design Principles Established

1. **Read-only dependencies:** Game install = library, never copy
2. **Version tracking:** .buildinfo records game version, runtime checks
3. **Build pipeline:** Human-readable source → optimized runtime
4. **Profile before optimize:** Learned from orbital mechanics case
5. **Performance non-negotiable:** <5s target drives all decisions
6. **Preserve operational data:** Remove rendering metadata, keep science

## Technical Decisions

### File Organization
```
src/          # Human edits
build/        # Optimized artifacts (gitignored)
generated/    # Runtime data (gitignored)
docs/         # Human documentation
.ai/      # Project directives
```

### Actor Files
- Specs: `actor_*.md` (14 files: 7 specs + 7 fluff)
- Fluff: Renamed from `*_examples.md` to `*_fluff.md`
- Structure: Background → Traits → Domain → Tiers → Fluff

### Version Tracking
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

## Unresolved / TODO

### High Priority
- Tier-specific prompts (18 files: 6 actors × 3 tiers)
- CODEX script-based evaluation logic
- Domain routing implementation
- Actual savegame field requirements

### Medium Priority
- Template optimization rules (after profiling)
- Runtime version checking implementation
- Conversation examples
- Performance monitoring

### Low Priority
- Build process enhancements (incremental, parallel)
- Director/validation system
- Advanced error recovery

## Insights & Lessons

1. **Orbital mechanics case:** User caught assumption (remove orbital data) because launch windows need it. Validates "profile before optimize" principle.

2. **Chuck's Pollyanna:** Traits matter. Initial fluff didn't match character sheet. Professional/off-duty mode split captures mercenary competence + cheerful cynicism.

3. **Template dependency:** Game updates invalidate copied data. Read-only dependency with version tracking is cleaner.

4. **File structure iterations:** Started complex, simplified to src/build pattern. Standard software conventions work.

5. **Documentation living docs:** FEATURES.md captures brainstorming. .ai/ preserves project context across sessions.

## File Inventory

**Created:**
- 14 actor files (src/actors/)
- 5 system docs (docs/)
- README.md, REFERENCE.md, FEATURES.md
- .env.dist, build/.buildinfo.example
- scripts/build.py
- .ai/ directory with instructions.md, context.md, this cache

**Status:** ~23 files, ~116KB, ready for implementation

## Next Session Candidates

1. CODEX evaluation logic (tier readiness calculation)
2. Domain routing (keyword → advisor mapping)
3. Prompt engineering (tier-specific prompts)
4. Savegame data requirements (what fields to extract)
5. Template usage profiling (which templates for which advisors)

**Session End:** 2026-02-14
