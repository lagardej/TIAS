# Actor Template

This template provides the structure for creating new advisors.

## Usage

1. Copy this entire `_template/` directory to `resources/actors/<actor_name>/`
2. Fill in all fields in `spec.toml`
3. Write persona content in `persona.md` (Background, Personality, Stage sections)
4. Add strings to `strings.csv` (openers and reactions)
5. Write example exchanges in `examples_tier1.md` (and tier2/3 when relevant)

## File Descriptions

### spec.toml
Structured metadata — machine config compiled into JSON/SQLite downstream.
- Identity (name, callsign, age, nationality)
- Traits (from game's TITraitTemplate)
- Domain expertise and keywords
- Tier progression (what they can discuss at each tier)
- Spectator behavior configuration
- Error messages

### persona.md
All prose content in one file with three sections:

**## Background** — Narrative history (200-500 words prose). Who they are, how they got here,
what drives them, their relationships. Written once, rarely changed.

**## Personality** — LLM instruction document. Voice, registers, behavioral rules, relationships,
limits. Structured with named subsections (e.g. `[voice]`, `[humor]`, `[domain]`, `[relationships]`, `[limits]`).
This is the primary document the LLM reads to inhabit the character.

**## Stage** — Spectator reactions (short lines with inline comments) and narrative stage
directions (in [brackets]). Used when the actor is observing, not advising.

### strings.csv
All sampled strings in one file. Used by the play command for variety.

**Columns:**
- `type`: `reaction` or `opener`
- `text`: The string (required)
- `category`: For reactions: general/professional/trolling/etc. For openers: mood (neutral/cheerful/etc.)
- `mode`: Delivery tone (reactions only)
- `trigger`: When applicable (reactions only)
- `note`: Internal comment (openers only)

**Reactions:** 20-50 entries. Used when actor is spectator.
**Openers:** 20-30 entries. Used when actor opens a session.

### examples_tier{N}.md
Dialogue examples showing voice and domain at each tier. 3-5 exchanges minimum.
Include at least one out-of-tier and one out-of-domain example per file.

---

## V2 Migration Note
`persona.md` sections map directly to `persona_fragments` table categories in V2 SQLite.
The section headers (`## Background`, `## Personality`, `## Stage`) are the migration key.
`strings.csv` maps to a `strings` table with the same columns.
`spec.toml` maps to the `actors` table.
