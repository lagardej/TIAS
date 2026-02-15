# WORKFLOW

## WORKFLOW

### Game Integration Phases

**Three-Phase Cycle:**

1. **PREPARATION PHASE** (Outside game, with chatbots)
   - Game paused at Assignment Phase
   - CODEX data synced (Valentina's intel represented by scripts)
   - User consults advisors via chat
   - Advisors analyze, recommend strategy
   - User decides strategy

2. **ASSIGNMENT PHASE** (In-game)
   - User assigns councilor missions based on strategy
   - Confirms assignments
   - Game enters Resolution Phase

3. **RESOLUTION PHASE** (In-game)
   - Missions execute automatically
   - No chat interaction
   - Game plays out

4. **NEXT ASSIGNMENT PHASE** → Return to Preparation Phase

### Data Sync Cycle

**Monthly Intelligence Cycle:**

**Assignment Phase Timing:**
- First ~4 months (until "New Normal" event, April-June 2026): Every 7 days
- After "New Normal": Every 14 days

**Sync Trigger:** Start of Assignment Phase (when player can assign missions)

**Sync Process:**
1. User runs: `python3 codex_inject.py savegame.json.gz`
2. Script extracts tier-filtered game state
3. CODEX evaluates tier readiness
4. Random advisor opens meeting
5. CODEX posts automatic status report
6. User can query advisors
7. Preparation phase active until user assigns missions

**Intelligence Lag:** Advisors always work with data from last Assignment Phase, creating realistic intel delay

### Preparation Phase Flow

**Automatic Start Sequence:**
1. Data injection completes
2. Random advisor selected
3. Advisor requests CODEX report (personality-matched opener)
4. CODEX posts tier + metrics evaluation
5. Chat ready for user queries

**During Preparation:**
- User queries advisors (1-2 become operational per query)
- Others participate as spectators (reactions/comments)
- Conversation builds within session
- History includes current + previous prep phase

**User Actions:**
- Ask strategic questions
- Request specific advisor input ("Ask Lin:")
- Query CODEX for data verification
- Manually provide missing data if errors occur

**Session End:**
- User returns to game
- Assigns missions
- Conversation history preserved
- Next prep phase will remember this session + previous

### Conversation Memory

**Two-Phase Memory System:**
- **Current prep phase:** Building now
- **Previous prep phase:** Reference available
- **Older history:** Cleared (bounded memory)

**Memory Reset:** At each new Assignment Phase
- New prep phase begins
- Current becomes previous
- Previous is cleared
- Fresh context for new strategic situation

**Benefits:**
- Advisors not goldfish (remember immediate past)
- Can reference "last session's strategy"
- Context stays bounded for performance
- Natural strategic continuity

### Tier Progression

**Tier System:**
- **Tier 1:** Early Consolidation (game start)
- **Tier 2:** Industrial Expansion (unlock at 60% readiness)
- **Tier 3:** Strategic Confrontation (unlock at 70% readiness)

**Unlock Process:**
1. CODEX evaluates tier readiness (script-based calculation)
2. Reports percentage and conditions met
3. User manually triggers unlock when ready
4. All advisors tier up together (global tier progression)

**Post-Unlock:**
- Load new tier-specific prompts for all advisors
- Expand context data filtering
- Advisors can now discuss tier-appropriate topics
- Previous tier knowledge retained

---

