"""
identify_actor.py — Resolve user input to 0, 1, or 2 actors.

Explicit routing: input contains a name or nickname from spec.toml.
Implicit routing: embedding similarity against actor domain vectors.

Returns an IdentifyResult with a list of ActorMatch objects and a flow_type.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import tomllib


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class FlowType(str, Enum):
    STANDARD        = "standard"
    DEBATE          = "debate"
    AMBIGUOUS       = "ambiguous"       # explicit match, 2+ candidates
    TOO_VAGUE       = "too_vague"       # implicit, 0 matches
    TOO_BROAD       = "too_broad"       # implicit, 3+ matches
    NO_MATCH        = "no_match"        # explicit, 0 matches


class AdvisorRole(str, Enum):
    MAIN    = "main"      # similarity >= 0.7
    SUPPORT = "support"   # 0.3 <= similarity < 0.7


@dataclass
class ActorSpec:
    """Minimal actor identity loaded from spec.toml."""
    actor_dir: Path
    first_name: str
    family_name: str
    nickname: str
    display_name: str

    @property
    def match_tokens(self) -> list[str]:
        """All name tokens that trigger explicit routing (lowercased)."""
        tokens = [self.first_name.lower()]
        if self.family_name:
            tokens.append(self.family_name.lower())
        if self.nickname:
            tokens.append(self.nickname.lower())
        return tokens


@dataclass
class ActorMatch:
    spec: ActorSpec
    role: AdvisorRole
    similarity: Optional[float] = None   # None for explicit matches


@dataclass
class IdentifyResult:
    flow_type: FlowType
    actors: list[ActorMatch] = field(default_factory=list)
    # Human-readable reason for stage directions (too_vague, too_broad, ambiguous)
    stage_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Actor loader
# ---------------------------------------------------------------------------

def load_actor_specs(actors_dir: Path) -> list[ActorSpec]:
    """
    Load all actor specs from resources/actors/.
    Skips _template and any directory without a spec.toml.
    """
    specs = []
    for actor_dir in sorted(actors_dir.iterdir()):
        if not actor_dir.is_dir() or actor_dir.name.startswith('_'):
            continue
        spec_path = actor_dir / "spec.toml"
        if not spec_path.exists():
            logging.warning(f"No spec.toml in {actor_dir.name}, skipping")
            continue
        with open(spec_path, "rb") as f:
            data = tomllib.load(f)
        specs.append(ActorSpec(
            actor_dir=actor_dir,
            first_name=data.get("first_name", ""),
            family_name=data.get("family_name", ""),
            nickname=data.get("nickname", ""),
            display_name=data.get("display_name", actor_dir.name),
        ))
    return specs


# ---------------------------------------------------------------------------
# Explicit routing
# ---------------------------------------------------------------------------

def _explicit_match(user_input: str, specs: list[ActorSpec]) -> list[ActorSpec]:
    """
    Return all actors whose first_name, family_name, or nickname
    appears as a word in the input (case-insensitive).
    """
    tokens = [t.strip(".,!?;:") for t in user_input.lower().split()]
    matched = []
    for spec in specs:
        if any(t in tokens for t in spec.match_tokens):
            matched.append(spec)
    return matched


# ---------------------------------------------------------------------------
# Implicit routing (embedding-based)
# ---------------------------------------------------------------------------

def _implicit_match(user_input: str, specs: list[ActorSpec]) -> list[tuple[ActorSpec, float]]:
    """
    Score each actor against the query using sentence embeddings.
    Returns list of (spec, similarity_score) for scores >= 0.3, sorted descending.

    Lazy-imports sentence_transformers so the module loads without it installed.
    Domain embeddings are loaded from each actor's spec.toml domain_keywords field
    and encoded on first call (pre-computation deferred to V2 DB migration).
    """
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        logging.error("sentence_transformers not installed — implicit routing unavailable")
        return []

    model = _get_embedding_model()
    query_vec = model.encode(user_input, convert_to_tensor=True)
    results = []

    for spec in specs:
        spec_path = spec.actor_dir / "spec.toml"
        with open(spec_path, "rb") as f:
            data = tomllib.load(f)
        keywords = data.get("domain_keywords", "")
        if not keywords:
            continue

        domain_vec = model.encode(keywords, convert_to_tensor=True)
        score = float(util.cos_sim(query_vec, domain_vec))

        if score >= 0.3:
            results.append((spec, score))

    return sorted(results, key=lambda x: x[1], reverse=True)


_embedding_model = None

def _get_embedding_model():
    """Return cached embedding model (all-MiniLM-L6-v2, CPU-side)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logging.info("Loading embedding model (all-MiniLM-L6-v2)...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def identify_actor(user_input: str, specs: list[ActorSpec]) -> IdentifyResult:
    """
    Resolve user input to 0, 1, or 2 actors.

    Tries explicit routing first. Falls back to implicit if no explicit match.
    """
    # --- Explicit ---
    explicit = _explicit_match(user_input, specs)

    if explicit:
        if len(explicit) == 1:
            return IdentifyResult(
                flow_type=FlowType.STANDARD,
                actors=[ActorMatch(spec=explicit[0], role=AdvisorRole.MAIN)],
            )
        # 2+ explicit matches → ambiguous, resolve in character
        return IdentifyResult(
            flow_type=FlowType.AMBIGUOUS,
            actors=[ActorMatch(spec=s, role=AdvisorRole.MAIN) for s in explicit],
            stage_note=f"Ambiguous: matches {', '.join(s.display_name for s in explicit)}",
        )

    # --- Implicit ---
    scored = _implicit_match(user_input, specs)

    if not scored:
        return IdentifyResult(
            flow_type=FlowType.TOO_VAGUE,
            stage_note="Query matched no advisor domain. Please be more specific.",
        )

    if len(scored) >= 3:
        names = ", ".join(s.display_name for s, _ in scored)
        return IdentifyResult(
            flow_type=FlowType.TOO_BROAD,
            stage_note=f"Query too broad — matches {names}. Narrow your scope.",
        )

    # 1 or 2 matches
    actors = []
    mains = [(s, score) for s, score in scored if score >= 0.7]
    supports = [(s, score) for s, score in scored if score < 0.7]

    for spec, score in mains:
        actors.append(ActorMatch(spec=spec, role=AdvisorRole.MAIN, similarity=score))
    for spec, score in supports:
        actors.append(ActorMatch(spec=spec, role=AdvisorRole.SUPPORT, similarity=score))

    # 2 mains OR 2 supports → debate (user arbitrates at end)
    # 1 main + 1 support → standard (main leads, support adds colour)
    flow = FlowType.DEBATE if len(actors) == 2 and len(mains) != 1 else FlowType.STANDARD

    return IdentifyResult(flow_type=flow, actors=actors)
