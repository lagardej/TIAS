# TIAS V2 — End-to-End Test Script

Tests cover session open, domain routing, cross-domain routing, and tier enforcement.
Run in sequence to simulate a natural session progression.

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
