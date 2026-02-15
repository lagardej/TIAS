# PERFORMANCE

## PERFORMANCE

### Target Metrics

**Primary Goal:** <5 second response time from query to complete answer

**Performance Budget Breakdown:**
```
Domain routing:        0.05s
Tier filtering:        0.20s
Load actor prompt:     0.10s
Context preparation:   0.30s
LLM generation:        2-3s   (200-300 tokens @ 60-100 tok/s)
Spectator reactions:   0.01s  (pre-written text append)
Format/display:        0.10s
-----------------------------------
Total:                 2.8-3.8s (well under 5s target)
```

**CODEX Evaluation:** ~0.1s (script-based, not LLM)

### Optimization Decisions

**Script-Based CODEX:**
- Tier evaluation via Python calculation
- Saves 1-2s vs LLM generation
- Deterministic and reliable
- Near-instant processing

**Tier-Specific Prompts:**
- 18 prompt files (6 actors × 3 tiers)
- Smaller prompts = faster processing
- Prevents knowledge leakage
- ~0.3s faster than single large prompts

**Tier-Filtered Context:**
- Tier 1: Basic metrics only
- Tier 2: + Mid-game systems
- Tier 3: + Full strategic data
- Smaller context = faster processing

**Pre-Written Fluff:**
- Opener variations (30 per advisor)
- Spectator reactions (20-45 per advisor)
- Stage directions (15-20 variants)
- Zero LLM cost (random selection)

**Probability-Based Spectators:**
- Chuck: 50% (but not consecutive)
- Valentina: 30%
- Others: 15-20%
- Pre-written quips, not LLM-generated

### Expected Performance

**Native Linux (Fedora) + RX 9070 XT:**
- Estimated: 60-100 tokens/second
- 250 token response: 2.5-4 seconds generation
- Total response time: 2.8-4.5 seconds
- **Consistently under 5s target**

**Performance Monitoring:**
- Log response times
- Track LLM generation speed
- Monitor context processing overhead
- Identify bottlenecks

**If Performance Degrades:**
- Reduce response length (200 tokens max)
- Clear conversation history more aggressively
- Simplify spectator reactions
- Check KoboldCPP configuration

---

