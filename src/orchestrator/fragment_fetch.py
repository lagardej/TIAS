"""
fragment_fetch.py — JIT persona fragment injection.

Reads fragments from persona.md (bracket-tagged sections) and spec.toml (base).
Returns only the fragments relevant to the current query and tier confidence.

Fragment categories:
    base         — synthesized from spec.toml identity fields (always injected)
    voice        — speech registers and tells (always injected)
    limits       — hard behavioral edges (always injected)
    domain       — operational vocabulary and expertise (domain keyword match)
    relationships — actor-specific relationship dynamic (other actor present)
    spectator    — short reaction lines (spectator path only)
    stage_directions — physical beat descriptions (scene-framing only)
"""

import logging
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from src.orchestrator.identify_actor import ActorSpec
from src.orchestrator.tier_check import TierConfidence


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

ALWAYS_INJECTED = {"voice", "limits"}
SPECTATOR_ONLY  = {"spectator", "stage_directions"}

TIER_HEDGE_INSTRUCTION = (
    "[NOTE: You are operating at the edge of your expertise for this tier. "
    "Acknowledge the gap honestly. Flag what you know, what you don't, "
    "and what would be needed to advise with full confidence.]"
)


@dataclass
class Fragment:
    category: str
    subject: str | None    # populated for 'relationships' only (target actor name)
    content: str


@dataclass
class FetchResult:
    actor: ActorSpec
    fragments: list[Fragment] = field(default_factory=list)

    def assembled(self) -> str:
        """Return all fragments joined for prompt injection."""
        return "\n\n".join(f.content for f in self.fragments)


# ---------------------------------------------------------------------------
# persona.md parser
# ---------------------------------------------------------------------------

def _parse_persona_fragments(persona_path: Path) -> dict[str, str]:
    """
    Extract [category] sections from persona.md ## Personality and ## Stage blocks.
    Returns dict of {category: content}.

    Sections are delimited by [tag] lines. Content runs until the next [tag] or ##.
    """
    text = persona_path.read_text(encoding="utf-8")
    fragments: dict[str, str] = {}

    # Match [tag] followed by content up to next [tag] or ## heading
    pattern = re.compile(
        r"^\[(\w+)\]\s*\n(.*?)(?=^\[|\Z|^##\s)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        category = match.group(1).lower()
        content  = match.group(2).strip()
        if content:
            fragments[category] = content

    return fragments


# ---------------------------------------------------------------------------
# base fragment (synthesized from spec.toml)
# ---------------------------------------------------------------------------

def _build_base(spec: ActorSpec, data: dict) -> Fragment:
    """
    Synthesize a minimal always-loaded identity fragment from spec.toml fields.
    Enough for the model to know who is speaking without leaking personality.
    """
    parts = [f"Name: {spec.display_name}"]
    if spec.nickname:
        parts.append(f"Known as: {spec.nickname}")
    if data.get("profession"):
        parts.append(f"Role: {data['profession']}")
    if data.get("domain_primary"):
        parts.append(f"Domain: {data['domain_primary']}")
    return Fragment(category="base", subject=None, content="\n".join(parts))


# ---------------------------------------------------------------------------
# Domain keyword match
# ---------------------------------------------------------------------------

def _domain_match(query: str, data: dict) -> bool:
    """Return True if any domain_keyword appears in the query (case-insensitive)."""
    keywords = [k.strip().lower() for k in data.get("domain_keywords", "").split(",") if k.strip()]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fragment_fetch(
    spec: ActorSpec,
    query: str,
    tier_confidence: TierConfidence,
    other_actor_names: list[str] | None = None,
    spectator_only: bool = False,
) -> FetchResult:
    """
    Fetch relevant fragments for an actor given the current query context.

    Args:
        spec:               Actor to fetch for.
        query:              User input (used for domain keyword match).
        tier_confidence:    From tier_check — FULL, HEDGED, or BLOCKED.
        other_actor_names:  Display names of other actors present (triggers relationships fetch).
        spectator_only:     If True, return spectator fragment only.
    """
    result = FetchResult(actor=spec)

    spec_path = spec.actor_dir / "spec.toml"
    persona_path = spec.actor_dir / "persona.md"

    with open(spec_path, "rb") as f:
        data = tomllib.load(f)

    parsed = _parse_persona_fragments(persona_path) if persona_path.exists() else {}

    # --- Spectator path ---
    if spectator_only:
        if "spectator" in parsed:
            result.fragments.append(Fragment(category="spectator", subject=None, content=parsed["spectator"]))
        else:
            logging.warning(f"{spec.display_name}: no spectator fragment found")
        return result

    # --- Always injected ---
    result.fragments.append(_build_base(spec, data))

    for cat in ALWAYS_INJECTED:
        if cat in parsed:
            result.fragments.append(Fragment(category=cat, subject=None, content=parsed[cat]))
        elif spec.first_name.lower() != "codex":  # CODEX has no voice/limits by design
            logging.warning(f"{spec.display_name}: missing '{cat}' fragment")

    # --- Domain match ---
    if _domain_match(query, data) and "domain" in parsed:
        result.fragments.append(Fragment(category="domain", subject=None, content=parsed["domain"]))

    # --- Relationships ---
    if other_actor_names:
        rel_content = parsed.get("relationships", "")
        if rel_content:
            for name in other_actor_names:
                # Extract the sub-section for this specific actor if present
                # Relationships fragment may contain named sub-sections (e.g. "JONNY (Jonathan Pratt):")
                name_upper = name.upper().split()[0]  # match on first token, uppercased
                sub = re.search(
                    rf"{name_upper}.*?(?=\n[A-Z]{{2,}}|\Z)",
                    rel_content,
                    re.DOTALL,
                )
                if sub:
                    result.fragments.append(
                        Fragment(category="relationships", subject=name, content=sub.group(0).strip())
                    )
                else:
                    # No sub-section found — inject full relationships block once
                    result.fragments.append(
                        Fragment(category="relationships", subject=None, content=rel_content)
                    )
                    break  # avoid duplicate full-block injection

    # --- Tier hedge instruction ---
    if tier_confidence == TierConfidence.HEDGED:
        result.fragments.append(
            Fragment(category="tier_hedge", subject=None, content=TIER_HEDGE_INSTRUCTION)
        )

    return result
