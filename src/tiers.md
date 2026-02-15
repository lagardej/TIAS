# TIERS

## TIER SYSTEM

### Global Tier Definitions

**Tier 1 - Early Consolidation**
**Focus:**
- Nation control and stability
- Bootstrap space economy
- Minimal militarization
- Research foundation

**Characteristics:**
- Fragile economy (losing one mine hurts badly)
- Single-nation focus
- Basic space presence
- No defensive fleets required
- No sustained military operations

**Tier 2 - Industrial Expansion**
**Focus:**
- Large-scale mining operations
- Federation consolidation
- Mission Control pressure management
- Defensive fleet necessity
- Industrial scaling

**Characteristics:**
- Resilient economy (can absorb setbacks)
- Multi-nation blocs
- Shipyard operations
- Defensive military capability
- Sustained resource production

**Tier 3 - Strategic Confrontation**
**Focus:**
- Sustained fleet production
- Strategic blocs and global alignment
- War economy scaling
- Alien/faction confrontation
- Long-term strategic warfare

**Characteristics:**
- War economy operational
- Global military operations
- Large-scale space combat
- Strategic resource competition
- Sustained attrition warfare

### Tier Unlock Conditions

**Tier 1 → Tier 2 Unlock**

**Readiness Threshold:** 60%

**Conditions Evaluated (2 of 5 required):**
1. ≥3 functional mining sites
2. First operational shipyard in orbit
3. Mission Control ≥ sustained pressure threshold (approaching capacity)
4. Major federation formed (EU consolidation, unified India, etc.)
5. Economic resilience: Can replace destroyed mine without collapse

**Readiness Calculation:**
- Each condition fully met: +20%
- Partial completion weighted proportionally
- Confidence multiplier based on data quality
- Final percentage = (base score) × (confidence)

**Philosophy:** Can you lose something and keep growing?

**Tier 2 → Tier 3 Unlock**

**Readiness Threshold:** 70% (higher bar for late-game transition)

**Conditions Evaluated:**
1. Sustained fleet production capacity
2. First major alien confrontation survived
3. Large-scale space combat capability demonstrated
4. Global bloc polarization evident
5. War economy operational

**Philosophy:** Can you sustain strategic warfare?

### CODEX Tier Evaluation

**Evaluation Method:** Script-based calculation

**Process:**
1. Parse savegame data
2. Count/evaluate each condition
3. Calculate base percentage
4. Apply confidence multiplier
5. Determine status (Stable/Approaching/Threshold Met)
6. Format structured report

**Status Levels:**
- **Stable:** Current tier well-established, not approaching next
- **Approaching:** 40-59% (Tier 1→2) or 50-69% (Tier 2→3)
- **Threshold Met:** ≥60% (Tier 1→2) or ≥70% (Tier 2→3), unlock available

**Confidence Levels:**
- **High (90-100%):** All metrics available, clear evaluation
- **Medium (60-89%):** Some metrics missing but tier determinable
- **Low (<60%):** Significant data gaps, tier held but uncertain

### Context Filtering by Tier

**Tier 1 Data Access:**
- Control points per nation
- Stability levels
- Influence income/spending
- Mine count and locations
- Basic power generation
- MC current/maximum
- Research progress (current techs)
- Nation GDP (basic)

**Tier 2 Adds:**
- Federation details and mechanics
- MC expansion options
- Shipyard status and capabilities
- Fleet count (basic)
- Economic interconnections
- Regional power dynamics
- Advanced research tree visibility

**Tier 3 Adds:**
- Complete fleet compositions
- Bloc alignments and tensions
- War economy metrics
- Attrition calculations
- Strategic resource competition
- Global military postures
- Long-term strategic visibility

**Implementation:** CODEX extraction script filters savegame based on current global tier before providing data to advisors.

---

