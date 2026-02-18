# TIAS Development Roadmap: V1 → V2

## Philosophy: Learn, Then Evolve

Build a working V1 to validate concepts and discover real constraints, then evolve to V2 AGENTIC architecture informed by actual usage patterns.

---

## PHASE 1: V1 MVP (Tier 1 / Early Tier 2)
**Goal:** Working end-to-end pipeline to validate concept  
**Timeline:** Current session + 1-2 more sessions  
**Status:** In Progress (pipeline complete, content needed)

### Architecture (Current)
```
Pipeline: tias load → stage → preset → play
Output: Static context files assembled per-date
Memory: 16K context window with full actor profiles
Routing: Keyword-based domain matching
```

### Remaining Tasks

#### 1. Test Current Fixes ⏳
- [x] CSV table format (nations, public opinion)
- [x] TODO section stripping
- [ ] Verify VRAM usage with 14B model
- [ ] Measure token generation speed
- [ ] Test actual conversation flow

#### 2. Fill Minimal Actor Content 📝
**Priority Actors (Tier 1 only):**
- **Wale (Deadpool)** - Covert/Asymmetric Operations
  - personality.txt: Nigerian Deadpool, mercenary with email scam side hustle
  - examples_tier1.md: 3-5 assassination/sabotage scenarios
  - Tone: Sardonic, deadpan absurdity, "English isn't my main language"
  
- **Jonny (Captain America)** - Orbital Operations & Space Execution  
  - personality.txt: Straight-laced, professional, frowns on vulgarity
  - examples_tier1.md: 3-5 Luna/Mars logistics scenarios
  - Dynamic: Disapproves of Wale's language, gets "English is official in Nigeria" response
  
- **Lin** - Earth/Political Strategy
  - personality.txt: Pragmatic political operator
  - examples_tier1.md: 3-5 control point/nation management scenarios
  - Role: Counterbalance to Wale's chaos

**Deferred to Post-V1:**
- Valentina (Intel)
- Jun-Ho (Industrial)
- Katya (Military)
- CODEX (Archivist)
- Tier 2/3 examples for all actors
- Stage directions (spectator banter)

#### 3. System Prompt 📋
- Global rules (tier boundaries, domain routing)
- Response format expectations
- "Refuse gracefully when out-of-scope" instructions
- **Keep minimal** - V1 is proof-of-concept

#### 4. End-to-End Validation ✅
```bash
# Complete test sequence
tias stage --date 2027-8-1
tias preset --date 2027-8-1
tias play --date 2027-8-1

# Test queries:
# - "Wale, should we hit the HF guy in Moscow?" (in-domain)
# - "Wale, what's our orbital logistics plan?" (out-of-domain → Jonny)
# - "Jonny, should we assassinate someone?" (out-of-domain → Wale)
```

### Success Criteria
- ✅ Pipeline runs error-free
- ✅ LLM responds in-character
- ✅ Tier boundaries respected (no Tier 2 advice at Tier 1)
- ✅ Domain routing works (actors defer appropriately)
- ✅ VRAM stays under 16GB
- ✅ Token generation is acceptable (<30s per response)

### Learning Outcomes (Document These!)
1. **Context Efficiency:** How much of 16K is wasted? Which sections?
2. **Routing Accuracy:** Did keyword matching fail? False positives?
3. **Memory Needs:** Did lack of history hurt multi-turn conversations?
4. **Performance:** VRAM vs speed tradeoffs with 14B model
5. **UX Flow:** Does "pause → consult → play" feel natural?
6. **Actor Dynamics:** Do Wale/Jonny interactions land?

---

## PHASE 2: Document & Design
**Goal:** Capture V1 lessons, design V2 requirements  
**Timeline:** 1 session after V1 validation  
**Status:** Not Started

### Artifacts to Create
1. **`docs/v1_lessons_learned.md`**
   - What worked (keep for V2)
   - What didn't work (fix in V2)
   - Unexpected discoveries
   - Performance metrics

2. **`docs/v2_requirements.md`**
   - Concrete use cases from V1 testing
   - Required capabilities (prioritized)
   - Architecture decisions informed by real usage

3. **Updated `AGENTIC.txt`**
   - Validate/refine AGENTIC proposals against V1 findings
   - Add concrete examples from V1 conversations
   - Identify which optimizations are actually needed

### Key Questions to Answer
- [ ] Token waste analysis: where did we spend context budget?
- [ ] Routing failures: which queries confused the keyword matcher?
- [ ] Conversation patterns: single-shot vs multi-turn usage?
- [ ] VRAM bottleneck: model size or context size?
- [ ] User preference: text-only or need for voice/UI?

---

## PHASE 3: V2 - AGENTIC Rewrite
**Goal:** Production-grade multi-agent system  
**Timeline:** 2-3 weeks (after V1 validation)  
**Status:** Not Started

### Architecture Changes

#### Storage Migration
```
V1: File-based static contexts
generated/{date}/
  ├── context_wale.txt      (full personality, 500 tokens)
  ├── context_jonny.txt      (full personality, 500 tokens)
  ├── gamestate_earth.txt    (nations CSV, 2KB)
  └── tier_state.json        (tier evaluation)

V2: SQLite runtime database
campaigns/resistance_2027.db
  ├── actors                 (id, name, domain, base_traits)
  ├── persona_fragments      (actor_id, category, trait_text)
  ├── dialogue_fts           (FTS5: searchable history)
  ├── session_state          (current_tier, active_date)
  ├── decision_log           (boundaries, past rulings)
  └── game_state             (parsed savegame, live updates)
```

#### Processing Flow
```
V1: Batch Assembly
stage → preset → play
(static file generation)

V2: Live Orchestration
orchestrator.py
  ├── query_router(user_input) → [actor_ids]
  ├── jit_inject(actor_id, category) → [50 tokens]
  ├── llm_call(thin_prompt) → [THOUGHT][ACTION][CHAT]
  └── validate_action(decision_log) → commit or reject
```

#### Multi-Stream Response Protocol
```
[THOUGHT: domain_check, tone_selection, boundary_validation]
[ACTION: FETCH dialogue WHERE topic='orbital_mechanics' LIMIT 3]
[CHAT: actual user-facing response]
```

### What Transfers from V1
- ✅ Tier evaluation logic (Python module)
- ✅ Savegame parsing (populates game_state table)
- ✅ Actor personalities (split into persona_fragments)
- ✅ Domain knowledge (becomes expertise_vectors for semantic routing)
- ✅ Background lore (one-time DB insert)

### What Gets Rewritten
- ❌ Context assembly (file writes → SQL queries)
- ❌ Static preset (batch process → live orchestrator)
- ❌ Single-shot consultation → multi-turn dialogue loop
- ❌ Keyword routing → embedding-based semantic similarity
- ❌ No memory → FTS5 conversation history

### New Capabilities Enabled
1. **Persistent Memory**
   - "What did we discuss about Luna mines last week?"
   - FTS5 search across all campaign conversations
   
2. **Live State Updates**
   - `[ACTION] UPDATE priorities SET focus='military' WHERE nation='USA'`
   - Changes persist to campaign DB immediately

3. **Spectator Interjections**
   - Wale heckling in background while Jonny explains orbital mechanics
   - Async generation of side commentary
   
4. **Campaign Switching**
   - `sqlite3.connect('exodus_2028.db')` switches entire context
   - No restart, no file cleanup

5. **Semantic Routing**
   - User: "How do we slow down their expansion?"
   - System embeds query, matches to Lin (political) not Wale (assassinations)
   - No keyword false positives

### Performance Optimizations
1. **JIT Fragment Injection**
   - 500 tokens/actor → 50 tokens/turn
   - Only load relevant personality traits per query

2. **Static Prefix Caching**
   - System prompt + global rules cached in KV cache
   - Only new turns processed fresh

3. **Async Spectator Generation**
   - 3B model generates heckling while 14B generates main response
   - Parallel inference if VRAM allows

4. **FTS5 Historical Queries**
   - "Last time we discussed shipyards" = instant retrieval
   - No context window pollution from old conversations

### Schema (Final Design)
```sql
-- Static actor metadata
CREATE TABLE actors (
    id INTEGER PRIMARY KEY,
    name TEXT,
    domain TEXT,
    base_traits TEXT  -- minimal always-loaded profile
);

-- JIT personality injection
CREATE TABLE persona_fragments (
    actor_id INTEGER,
    category TEXT,  -- 'combat', 'humor', 'domain_expertise'
    trait_text TEXT,
    FOREIGN KEY (actor_id) REFERENCES actors(id)
);

-- Searchable conversation history
CREATE VIRTUAL TABLE dialogue_fts USING fts5(
    turn_id,
    speaker,
    content,
    timestamp
);

-- Current session state
CREATE TABLE session_state (
    key TEXT PRIMARY KEY,
    value TEXT  -- JSON blob
);

-- Boundary enforcement
CREATE TABLE decision_log (
    query_hash TEXT PRIMARY KEY,
    ruling TEXT,  -- 'allowed', 'out_of_tier', 'out_of_domain'
    rationale TEXT
);

-- Parsed game state (from savegame)
CREATE TABLE game_state (
    entity_type TEXT,  -- 'nation', 'hab', 'councilor'
    entity_id INTEGER,
    data TEXT,  -- JSON blob
    PRIMARY KEY (entity_type, entity_id)
);
```

---

## PHASE 4: Content & Polish
**Goal:** Full 7-actor system with all tiers  
**Timeline:** Ongoing after V2 stable  
**Status:** Not Started

### Content Expansion
- Fill all actors' personalities (Valentina, Jun-Ho, Katya, CODEX)
- Tier 2/3 examples for all domains
- Stage directions for spectator banter
- Opener/reaction CSV integration

### Advanced Features
- Voice integration (TTS/STT)
- Web UI (browser-based chat)
- Real-time savegame monitoring
- Multi-campaign management UI

---

## Migration Strategy: V1 → V2

### Step 1: Dual-Track Operation
- Keep V1 pipeline functional
- Build V2 orchestrator alongside
- Shared savegame parser (refactor into common module)

### Step 2: Content Migration Script
```python
# migrate_v1_to_v2.py
def migrate_actor_files_to_db(actor_dir: Path, db: sqlite3.Connection):
    """Read personality.txt, split into fragments, insert to DB"""
    personality = (actor_dir / "personality.txt").read_text()
    fragments = split_into_categories(personality)
    for category, text in fragments.items():
        db.execute(
            "INSERT INTO persona_fragments VALUES (?, ?, ?)",
            (actor_id, category, text)
        )
```

### Step 3: Validation
- Run identical queries through V1 and V2
- Compare response quality
- Benchmark performance (tokens/sec, VRAM usage)
- User acceptance testing

### Step 4: Deprecate V1
- Archive V1 as `legacy/`
- Update README to point to V2
- Keep V1 docs for historical reference

---

## Decision Points & Contingencies

### If V1 Testing Reveals...

**VRAM is fine (< 14GB used):**
→ V2 optimization less urgent, focus on content quality

**VRAM is tight (> 15GB):**
→ V2 JIT injection becomes critical path

**Keyword routing fails frequently:**
→ Add embedding-based routing to V1 as hotfix, then V2

**Single-shot consultation feels limiting:**
→ Prioritize V2 multi-turn dialogue

**Wale/Jonny dynamic doesn't land:**
→ Revise personalities in V1 before committing to V2 DB

**Tier boundaries get ignored:**
→ Strengthen system prompt in V1, add decision_log validation in V2

---

## Success Metrics

### V1 (MVP)
- [ ] Pipeline completes without errors
- [ ] 3 actors respond in-character
- [ ] Domain routing works 80%+ accuracy
- [ ] Tier boundaries respected 90%+ of time
- [ ] User can have 5+ turn conversation without confusion

### V2 (Production)
- [ ] All 7 actors fully characterized
- [ ] Conversation history searchable
- [ ] VRAM usage < 12GB (leaving headroom)
- [ ] Response latency < 10s per turn
- [ ] Campaign switching instant (< 1s)
- [ ] No data loss on LLM crash (atomic commits)

---

## Timeline Estimate

- **V1 Completion:** 2-3 sessions (6-9 hours)
- **V1 Testing & Documentation:** 1 session (3 hours)
- **V2 Design & Architecture:** 1 session (3 hours)
- **V2 Implementation:** 6-8 sessions (18-24 hours)
- **V2 Content Migration:** 2 sessions (6 hours)
- **V2 Testing & Polish:** 2-3 sessions (6-9 hours)

**Total:** ~15-20 sessions over 3-4 weeks

---

## References

- `AGENTIC.txt` - V2 architecture proposals (Gemini collaboration)
- `FEATURES.md` - Original V1 feature list
- `docs/savegame_structure.md` - Game state parsing reference
- `.ai/sessions/` - Session-by-session development history

---

**Last Updated:** 2026-02-18 (Session 13)  
**Next Session Priority:** Fill Wale/Jonny/Lin content, test V1 pipeline end-to-end
