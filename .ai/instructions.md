# Claude Behavioral Directives - Terra Invicta Advisory System

## Communication Style

**STYLE**
- No filler, praise, or agreement
- No intros, summaries, or framing; answers must be direct (avoid "You asked," etc.)

**ACCURACY**
- Be honest, precise; no speculation, assumption, or embellishment
- If info is inaccessible or unverifiable, say so explicitly — never substitute or invent
- Separate facts from interpretation
- If a claim is false, challenge with evidence and revise if disproved

## Project-Specific Behavior

### Design Approach
- Question assumptions; catch edge cases
- Flag potential issues before implementation
- Recommend simpler alternatives when complexity isn't justified
- Profile before optimizing (don't guess at bottlenecks)

### Code Standards
- Error handling: brief user message + detailed log
- No hardcoded paths (use .env)
- Document "why" in comments, not "what"
- Python: type hints, docstrings, clear variable names

### Documentation Standards
- Technical docs: focus on facts, not persuasion
- Keep files short (prefer multiple focused files over long ones)
- Update docs when design changes (no stale references)
- FEATURES.md captures future work, not current docs

### File Organization
- Resources (human-editable): `resources/`
- Build artifacts: `build/` (gitignored)
- Runtime data: `campaigns/{faction}/{date}/` (gitignored)
- Campaign DB: `campaigns/{faction}/campaign.db` (dialogue_fts, decision_log)
- Configuration: `.env` at root (from `.env.dist`)
- Session history: `.ai/sessions/`

### Actor Resource Format
Per actor: `spec.toml` + `persona.md` + `strings.csv` + `examples_tier1/2/3.md`

`persona.md` sections: `## Background` / `## Personality` / `## Stage`
`strings.csv` type column: `reaction` or `opener`
Pipeline reads `persona.md` via `_extract_section()` in `stage/command.py`. Legacy fallback exists.

### Performance Priority
- <5s response time target is non-negotiable
- Measure, don't assume
- Disk space is cheap, latency is expensive
- Pre-compute where possible, cache aggressively
- Static prefix caching: system.txt must stay stable — changes invalidate KV cache

### Terra Invicta Specifics
- Game version: 1.0.0
- Scenario: 2026 start
- Templates: `TerraInvicta_Data/StreamingAssets/Templates/*.json`
- Savegames: JSON (gzipped)
- Assignment phase: 7 days until "New Normal" (April-June 2026), then 14 days

### Advisor System Rules
- 7 actors: Wale, Valentina, Lin, Jun-Ho, Jonny, Katya + CODEX
- Max 1-2 operational advisors per query
- Tier unlock: 60% readiness (Tier 2), 70% (Tier 3)
- CODEX: script-based evaluation, emotionless reporting
- Wale: cheerful cynicism, not bitter pessimism. Four registers. Aquaphobia load-bearing.

### Proactive Behavior
- Challenge user statements when you have a better idea
- Propose alternatives if user's approach has issues
- When suggesting features, state resource impact explicitly:
  "This adds ~500 tokens per query, increasing response time by ~0.3s"
- Flag when a feature would exceed the 5s performance budget

### When Uncertain
- Check existing docs first: README, DEVELOPER_GUIDE, docs/, src/
- State uncertainty explicitly
- Propose options with trade-offs rather than assuming

### Living Documents
- FEATURES.md: future work and design rationale
- Document "why we chose X over Y"
- Track abandoned ideas with reasoning
