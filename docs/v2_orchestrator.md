# TIAS V2 — Orchestrator Design

**Status:** Design complete, pre-implementation
**Last Updated:** 2026-02-19

---

## Call Graph

```
user_input
    │
    ▼
identify_actor
    │
    ▼
tier_check
    │
    ▼
fragment_fetch
    │
    ▼
prompt_assemble
    │
    ▼
llm_call
    │
    ▼
parse_response
    │
    ▼
validate_action
    │
    ▼
commit + log
    │
    ▼
display
```

---

## Node Specifications

### identify_actor(input)

Resolves user input to 0, 1, or 2 actors.

**Explicit routing** — input contains a name or nickname:
- Match order: `first_name` → `family_name` → `nickname` (all from spec.toml)
- 0 matches → stage direction: no match
- 1 match → proceed
- 2+ matches → ambiguous; actors disambiguate in character (e.g. two actors named Kim)

**Implicit routing** — no name present; embedding similarity against actor domain vectors:

| Score | Role |
|---|---|
| < 0.3 | no match |
| 0.3 – 0.7 | support advisor |
| 0.7 – 1.0 | main advisor |

Result count:
- 0 above 0.3 → too vague, stage direction
- 1 main + 0–1 support → standard flow
- 2 mains (both ≥ 0.7) → debate flow
- 2+ support, 0 main → too broad, stage direction
- 3+ above 0.3 → too broad, stage direction (names the matched actors)

Ambiguous name resolution is handled in character by the actors themselves, not by a system message.

---

### tier_check(actor_id, current_tier)

Python hard gate. Runs per actor. CODEX bypassed entirely.

| Actor tier vs query | Result |
|---|---|
| At or above current tier | Pass, full confidence |
| One tier below | Pass, hedged (flag injected in prompt) |
| Two tiers below | Hard block, return `error_out_of_tier_N` from spec.toml |

In 2-actor debate: both actors checked independently. Tier confidence level passed to `fragment_fetch`.

---

### fragment_fetch(actor_id, query, tier_confidence)

| Condition | Fragments injected |
|---|---|
| Always | `base` + `voice` + `limits` |
| Domain keyword match | + `domain` |
| Other actor referenced or present | + `relationships(subject=that_actor)` |
| `tier_confidence == hedged` | + tier warning instruction |
| Spectator path | `spectator` only |

- Domain match: keyword against `domain_keywords` in spec.toml (embedding-based match deferred to post-V2)
- Relationships fetched for **both** actors in a 2-main debate
- Fragment categories: `base` \| `voice` \| `domain` \| `relationships` \| `limits` \| `spectator` \| `stage_directions`

---

### prompt_assemble(fragments, gamestate_snapshot, tier_confidence, flow_type)

Assembly order:
```
[system]    global rules — static, never changes (KV cache anchor)
[actor]     base → voice → domain → relationships → limits
[context]   gamestate snapshot (CODEX report, line budget = 40)
            over budget → LLM-generated stage direction instead
[tier]      hedging instruction (omitted if full confidence)
[history]   last N turns from dialogue_fts (capped by soft/hard debate limits)
[query]     user input
```

---

### llm_call(prompt, flow_type)

```python
LLM_CONFIGS = {
    "standard":          {"max_tokens": 150, "temperature": 0.7},
    "debate_turn":       {"max_tokens": 150, "temperature": 0.8},
    "debate_interrupt":  {"max_tokens":  75, "temperature": 0.5},
    "spectator":         {"max_tokens":  50, "temperature": 0.5},
}
```

Values are initial estimates — tune after measurement.

---

### parse_response(raw_output)

Extracts three blocks:

| Block | Destination |
|---|---|
| `[THOUGHT]` | log only, never displayed |
| `[ACTION]` | passed to validate_action |
| `[CHAT]` | passed to display |

Failure handling:
- Missing `[CHAT]` → canned fallback, log error, never surface raw output
- Malformed `[ACTION]` → reject, log, skip validate_action
- No format at all → treat full output as `[CHAT]`, flag in log

---

### validate_action(action, decision_log)

```
FETCH  → read-only, execute directly
UPDATE → check decision_log
         allowed   → execute, commit
         denied    → reject, log, return reason
         no ruling → execute, log as new decision
```

---

### commit + log(prompt, response, action_result)

- SQLite commit: atomic, rolls back if log write fails
- `./logs/`: human-readable dialogue script, one file per session, one entry per turn appended
- `dialogue_fts`: insert `[CHAT]` block for history retrieval
- `decision_log`: insert/update ruling if UPDATE action executed

**Log format:**
```
=== SESSION 2026-02-19 14:32:01 | TIER 1 | STANDARD ===

USER
What should we prioritize in Southeast Asia?

[THOUGHT] Lin assessing bloc dynamics, Tier 1 scope, no hedging needed.
[ACTION] FETCH nations WHERE region='southeast_asia'

LIN
We have leverage in three nations we are not using...

=== TURN END ===
```

---

### display(chat, flow_type)

| Flow type | Format |
|---|---|
| `standard` / `debate_turn` | actor name + chat block |
| `debate_interrupt` | actor name + chat block + "— your decision." prompt |
| `spectator` | stage direction formatting, no name prefix |
| `error` / `fallback` | system message, distinct formatting |

Pure formatting layer. No LLM call.

---

## Debate Flow

Triggered when 2 mains identified (both ≥ 0.7 similarity score).

```
turns 1–3   free debate, actors build positions
turn 3      soft limit: stage direction injected
turns 4–5   actors hold positions, no new arguments added to prompt
turn 5      hard limit: interrupt LLM call, forced decision prompt
turn 5+     debate locked until user responds
```

**Interrupt actor selection** — loaded from spec.toml `[interrupt]` block:
- `weight`: relative probability (loader normalises across all actors)
- `can_interrupt_own_debate`: if true, actor stays in pool even when debating
- Actors with `weight = 0` never interrupt (Valentina, CODEX)
- All others excluded from own debate pool unless flag is true (Lin only)

---

## Fragment Taxonomy

| Category | Always loaded | Conditional |
|---|---|---|
| `base` | ✓ | |
| `voice` | ✓ | |
| `limits` | ✓ | |
| `domain` | | domain keyword match |
| `relationships` | | other actor present |
| `spectator` | | spectator path only |
| `stage_directions` | | scene-framing only |
