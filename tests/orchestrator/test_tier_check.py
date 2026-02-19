"""
tests/orchestrator/test_tier_check.py

Unit tests for src/orchestrator/tier_check.py.
Uses real actor specs where possible; fixtures for edge cases.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.orchestrator.identify_actor import ActorMatch, AdvisorRole, load_actor_specs
from src.orchestrator.tier_check import (
    TierConfidence,
    tier_check,
    tier_check_all,
)

ACTORS_DIR    = Path("resources/actors")
FIXTURES_DIR  = Path("tests/fixtures/actors")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def specs():
    return load_actor_specs(ACTORS_DIR)


@pytest.fixture(scope="module")
def fixture_specs():
    return load_actor_specs(FIXTURES_DIR)


def _match(specs, name: str) -> ActorMatch:
    """Helper: find actor by first_name, family_name, nickname, or display_name token."""
    for s in specs:
        targets = [s.first_name.lower(), s.family_name.lower(), s.nickname.lower(),
                   s.display_name.lower()]
        if name.lower() in targets:
            return ActorMatch(spec=s, role=AdvisorRole.MAIN)
    raise ValueError(f"Actor '{name}' not found in specs")


# ---------------------------------------------------------------------------
# Single actor checks
# ---------------------------------------------------------------------------

class TestTierCheck:

    def test_actor_at_current_tier(self, fixture_specs):
        result = tier_check(_match(fixture_specs, "tier1"), current_tier=1)
        assert result.confidence == TierConfidence.FULL
        assert result.error_message is None

    def test_actor_one_tier_below(self, fixture_specs):
        # tier1-only actor at Tier 2 — hedged
        result = tier_check(_match(fixture_specs, "tier1"), current_tier=2)
        assert result.confidence == TierConfidence.HEDGED
        assert result.error_message is None

    def test_actor_two_tiers_below(self, fixture_specs):
        # tier1-only actor at Tier 3 — blocked
        result = tier_check(_match(fixture_specs, "tier1"), current_tier=3)
        assert result.confidence == TierConfidence.BLOCKED
        assert result.error_message is not None

    def test_codex_bypasses_tier_check(self, specs):
        result = tier_check(_match(specs, "CODEX"), current_tier=3)
        assert result.confidence == TierConfidence.FULL

    def test_error_message_from_spec(self, fixture_specs):
        result = tier_check(_match(fixture_specs, "tier1"), current_tier=3)
        assert "tier" in result.error_message.lower() or "scope" in result.error_message.lower()


# ---------------------------------------------------------------------------
# Debate: two actors checked independently
# ---------------------------------------------------------------------------

class TestTierCheckAll:

    def test_both_pass(self, specs):
        actors = [_match(specs, "Jonny"), _match(specs, "Lin Mei-hua")]
        results = tier_check_all(actors, current_tier=1)
        assert all(r.confidence == TierConfidence.FULL for r in results)

    def test_one_hedged_one_full(self, specs, fixture_specs):
        # tier1-only fixture actor at tier 2 → hedged; Jonny (full spec) → full
        actors = [_match(fixture_specs, "tier1"), _match(specs, "Jonny")]
        results = tier_check_all(actors, current_tier=2)
        confidences = {r.actor.spec.nickname or r.actor.spec.first_name: r.confidence for r in results}
        assert confidences["tier1"] == TierConfidence.HEDGED
        assert confidences["Jonny"] == TierConfidence.FULL

    def test_one_blocked_collapses_to_standard(self, specs, fixture_specs):
        # Caller handles BLOCKED — tier_check_all just reports
        actors = [_match(fixture_specs, "tier1"), _match(specs, "Jonny")]
        results = tier_check_all(actors, current_tier=3)
        blocked = [r for r in results if r.confidence == TierConfidence.BLOCKED]
        passing = [r for r in results if r.confidence != TierConfidence.BLOCKED]
        assert len(blocked) == 1
        assert len(passing) == 1
