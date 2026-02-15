# Actor Template

This template provides the structure for creating new advisors.

## Usage

1. Copy this entire `_template/` directory to `src/actors/<actor_name>/`
2. Fill in all fields in `spec.toml`
3. Write background story in `background.txt`
4. Add 20-30 opener variations to `openers.csv`
5. Add 20-50 spectator reactions to `reactions.csv`
6. Run `python3 scripts/build.py` to generate build artifacts

## File Descriptions

### spec.toml
Structured metadata for the actor:
- Identity (name, age, nationality)
- Traits (from game's TITraitTemplate)
- Domain expertise and keywords
- Tier progression (what they can discuss at each tier)
- Spectator behavior configuration
- Error messages

### background.txt
Prose background story (200-500 words). Used to generate personality prompts.

### openers.csv
Meeting opener variations (20-30 entries). One is randomly selected when this advisor opens a preparation phase.

**Columns:**
- `text`: The opener string (required)
- `mood`: Tone (neutral, cheerful, serious, etc.) - optional
- `note`: Internal comment - optional

### reactions.csv
Spectator reaction pool (20-50 entries). Used when this advisor is spectator, not operational.

**Columns:**
- `text`: The reaction string (required)
- `category`: Type (general, professional, trolling, inappropriate, approval) - required
- `mode`: Delivery tone (professional, cheerful, serious, cynical) - required
- `trigger`: When applicable (domain name, "any", context) - optional

## Guidelines

**Openers:**
- Should request CODEX report
- Match actor personality
- 20-30 variations minimum to avoid repetition
- Can include stage directions: [cheerful], [deadpan], etc.

**Reactions:**
- Cover multiple situations (agreement, disagreement, domain mismatch, approval, concern)
- Match personality in both content and delivery
- Professional category for domain-specific comments
- General category for off-duty personality
- 20 minimum, 50+ for high-probability spectators (like Chuck at 50%)

**Spectator Probability:**
- Default: 0.15-0.20 (15-20% chance)
- High for chatty characters: 0.30-0.50 (Chuck, Valentina)
- Constraint: "not_consecutive" prevents dominating every conversation

**Tier Scope:**
- Each tier adds capability, doesn't replace previous
- Tier 1: Tactical, immediate concerns
- Tier 2: Strategic, regional/bloc level
- Tier 3: Global, long-term operations
- Be specific about what's restricted at each tier

## Example: Chuck

See `src/actors/chuck/` for a fully developed example showing:
- Pollyanna trait (cheerful cynicism)
- Professional/off-duty mode split
- High spectator probability (0.50) with not_consecutive constraint
- Domain-specific vs general reactions
- Rich background informing personality
