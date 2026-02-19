"""
tier_check.py — Python hard gate for tier enforcement.

Runs per actor before any LLM call. CODEX is bypassed entirely.
Returns a TierResult per actor indicating pass/hedged/blocked.
"""

import logging
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.orchestrator.identify_actor import ActorMatch, ActorSpec


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class TierConfidence(str, Enum):
    FULL    = "full"     # actor at or above current tier
    HEDGED  = "hedged"   # actor one tier below query
    BLOCKED = "blocked"  # actor two tiers below query


@dataclass
class TierResult:
    actor: ActorMatch
    confidence: TierConfidence
    # Populated when BLOCKED — in-character error message from spec.toml
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Tier constants
# ---------------------------------------------------------------------------

TIERS = [1, 2, 3]

# Maps current_tier → error key in spec.toml for one-tier-above queries
_TIER_ERROR_KEYS = {
    1: "error_out_of_tier_1",
    2: "error_out_of_tier_2",
}

CODEX_NAME = "codex"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_spec(spec: ActorSpec) -> dict:
    spec_path = spec.actor_dir / "spec.toml"
    with open(spec_path, "rb") as f:
        return tomllib.load(f)


def _is_codex(spec: ActorSpec) -> bool:
    return spec.first_name.lower() == CODEX_NAME


def _tier_gap(actor_max_tier: int, current_tier: int) -> int:
    """
    How many tiers below the query is this actor?
    Negative or zero means actor can handle the current tier.
    """
    return current_tier - actor_max_tier


def _actor_max_tier(data: dict) -> int:
    """
    Infer the highest tier this actor can handle from spec.toml.
    An actor supports a tier if its tier_N_scope is non-empty.
    """
    max_tier = 1
    for t in TIERS:
        if data.get(f"tier_{t}_scope", "").strip():
            max_tier = t
    return max_tier


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def tier_check(actor: ActorMatch, current_tier: int) -> TierResult:
    """
    Check whether an actor can operate at the current tier.

    CODEX bypassed — always returns FULL confidence.
    current_tier: integer 1–3 representing the campaign's unlocked tier.
    """
    if _is_codex(actor.spec):
        return TierResult(actor=actor, confidence=TierConfidence.FULL)

    data = _load_spec(actor.spec)
    max_tier = _actor_max_tier(data)
    gap = _tier_gap(max_tier, current_tier)

    if gap <= 0:
        return TierResult(actor=actor, confidence=TierConfidence.FULL)

    if gap == 1:
        logging.info(
            f"{actor.spec.display_name}: one tier below current ({max_tier} vs {current_tier}) — hedged"
        )
        return TierResult(actor=actor, confidence=TierConfidence.HEDGED)

    # gap >= 2 → blocked
    error_key = _TIER_ERROR_KEYS.get(max_tier, "error_out_of_tier_1")
    error_msg = data.get(error_key, "").strip() or (
        f"{actor.spec.display_name} cannot advise at Tier {current_tier}."
    )
    logging.info(
        f"{actor.spec.display_name}: blocked (actor max tier {max_tier}, current {current_tier})"
    )
    return TierResult(actor=actor, confidence=TierConfidence.BLOCKED, error_message=error_msg)


def tier_check_all(actors: list[ActorMatch], current_tier: int) -> list[TierResult]:
    """
    Run tier_check for each actor independently.
    Used for both standard flow and 2-actor debate.
    """
    return [tier_check(a, current_tier) for a in actors]
