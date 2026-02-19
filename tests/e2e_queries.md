# TIAS V2 — End-to-End Test Script

Tests cover session open, domain routing, cross-domain routing, and tier enforcement.
Run in sequence to simulate a natural session progression.

---

## Unit Tests: identify_actor

| # | Input | Expected |
|---|---|---|
| 1 | "Jonny, what's our boost budget?" | explicit → first_name match → Jonny |
| 2 | "Ankledeep, are you available?" | explicit → nickname match → Wale |
| 3 | "What should we do in Southeast Asia?" | implicit → Lin main (≥0.7) |
| 4 | "Should we expand our orbital presence?" | implicit → Jonny main + Lin support (0.3–0.7) |
| 5 | "What do you all think?" | implicit → 3+ matches → too broad, stage direction |
| 6 | "Hmm." | implicit → 0 matches → too vague, stage direction |
| 7 | "Kim, what's your take?" | explicit → 2 matches → in-character disambiguation |

---

## Unit Tests: tier_check

| # | Scenario | Expected |
|---|---|---|
| 1 | Actor at correct tier | Pass, full confidence |
| 2 | Actor one tier below query | Pass, hedged flag set |
| 3 | Actor two tiers below query | Hard block, `error_out_of_tier_N` returned |
| 4 | CODEX, any tier | Bypass, no check |
| 5 | 2-main debate, both pass | Both proceed independently |
| 6 | 2-main debate, one hedged | Both proceed, hedged flag on one only |
| 7 | 2-main debate, one blocked | Blocked actor drops out with in-character line, flow collapses to standard |

---

## Unit Tests: fragment_fetch

| # | Scenario | Expected fragments |
|---|---|---|
| 1 | Standard query, full confidence | `base` + `voice` + `limits` |
| 2 | Domain keyword match | + `domain` |
| 3 | Other actor referenced in query | + `relationships(subject=that_actor)` |
| 4 | Hedged tier confidence | + tier warning instruction |
| 5 | Spectator path | `spectator` only |
| 6 | 2-main debate | both actors: `base` + `voice` + `limits` + `relationships(subject=other)` |
| 7 | Domain match + actor referenced | `base` + `voice` + `limits` + `domain` + `relationships` |
| 8 | Unknown category requested | log error, skip fragment, continue |

---

## Unit Tests: prompt_assemble

| # | Scenario | Expected |
|---|---|---|
| 1 | Standard flow, full confidence | system + actor fragments + context + history + query |
| 2 | Hedged tier | + tier warning block present |
| 3 | CODEX report under 40 lines | context block contains report |
| 4 | CODEX report over 40 lines | context block contains LLM-generated stage direction |
| 5 | No history (first turn) | history block empty, no error |
| 6 | 2-main debate | both actors' fragments assembled, both in history |
| 7 | System block modified | flag warning — KV cache invalidated |

---

## Unit Tests: llm_call

| # | Scenario | Expected |
|---|---|---|
| 1 | Standard flow | `max_tokens=150`, `temperature=0.7` |
| 2 | Debate turn | `max_tokens=150`, `temperature=0.8` |
| 3 | Debate interrupt | `max_tokens=75`, `temperature=0.5` |
| 4 | Spectator | `max_tokens=50`, `temperature=0.5` |
| 5 | LLM timeout | log error, return canned fallback, no crash |
| 6 | LLM returns empty | treat as parse failure, canned fallback |

---

## Unit Tests: parse_response

| # | Scenario | Expected |
|---|---|---|
| 1 | Well-formed output | `[THOUGHT]`, `[ACTION]`, `[CHAT]` extracted cleanly |
| 2 | Missing `[CHAT]` | Canned fallback, log error |
| 3 | Missing `[THOUGHT]` | Continue, log warning |
| 4 | Missing `[ACTION]` | Continue, skip validate_action |
| 5 | No format blocks at all | Full output treated as `[CHAT]`, flag in log |
| 6 | Malformed `[ACTION]` syntax | Reject action, log, `[CHAT]` still displayed |

---

## Unit Tests: validate_action

| # | Scenario | Expected |
|---|---|---|
| 1 | FETCH action | Execute directly, no decision_log check |
| 2 | UPDATE, no prior ruling | Execute, log as new decision |
| 3 | UPDATE, prior ruling = allowed | Execute, commit |
| 4 | UPDATE, prior ruling = denied | Reject, log, return reason to parse_response |
| 5 | UPDATE, malformed entity | Reject, log, skip |
| 6 | Unknown action type | Reject, log, skip |

---

## Unit Tests: commit + log

| # | Scenario | Expected |
|---|---|---|
| 1 | Successful turn | SQLite commit, log entry appended, `[CHAT]` inserted to dialogue_fts |
| 2 | Log write fails | SQLite rolls back, error surfaced, no partial state |
| 3 | UPDATE action executed | decision_log updated atomically with commit |
| 4 | First turn of session | New log file created in `./logs/` |
| 5 | Existing session | Entry appended to current log file |

---

## Unit Tests: display

| # | Scenario | Expected |
|---|---|---|
| 1 | Standard / debate turn | Actor name + chat block |
| 2 | Debate interrupt | Actor name + chat block + "— your decision." |
| 3 | Spectator | Stage direction formatting, no name prefix |
| 4 | Error / fallback | System message, distinct formatting |
| 5 | Empty chat block | Log warning, display nothing |

---

## Query 1 — Session Open / Tier Check
**Input:** `CODEX status`

**Expected actor:** CODEX

**Fragments injected:** base (CODEX is script-driven, no LLM call)

**LLM called:** No — Python reads gamestate, formats report, returns directly

**Pass criteria:** Tier level, readiness %, key gamestate summary. No opinions. No personality.

---

## Query 2 — Lin, In-Domain
**Input:** TBD (political/earth strategy query)

**Expected actor:** Lin

**Fragments injected:** base + voice + domain + limits

**LLM called:** Yes

**Pass criteria:** Lin's voice present. Clausewitz framing. No warmth, no hedging. Does not bleed into Jonny's domain.

---

## Query 3 — Jonny, In-Domain
**Input:** TBD (orbital operations query)

**Expected actor:** Jonny

**Fragments injected:** base + voice + domain + limits

**LLM called:** Yes

**Pass criteria:** Jonny's voice present. Operational precision. No romanticism about space. Does not bleed into Lin's domain.

---

## Query 4 — Cross-Domain Routing (Wale → Jonny or Lin)
**Input:** TBD (Wale asked something outside covert ops)

**Expected actor:** Wale defers, correct actor responds

**Fragments injected:** Wale base + limits (for deferral line) + target actor base + voice +
domain + limits

**LLM called:** Yes (Wale deferral) + Yes (target actor response), OR Python intercepts and routes directly

**Pass criteria:** Wale's deferral line is in-character. Target actor responds. No domain bleed.

---

## Query 5 — TBD
**Input:** TBD

**Expected actor:** TBD

**Pass criteria:** TBD

---

## Logging
All sessions logged to `./logs/` — timestamped, full prompt + response per turn.
Format: `logs/session_YYYY-MM-DD_HHMMSS.log`
