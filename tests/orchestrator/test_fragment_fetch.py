"""
tests/orchestrator/test_fragment_fetch.py

Unit tests for src/orchestrator/fragment_fetch.py.
Uses real actor specs and persona.md files from resources/actors/.
"""

from pathlib import Path

import pytest

from src.orchestrator.identify_actor import load_actor_specs
from src.orchestrator.tier_check import TierConfidence
from src.orchestrator.fragment_fetch import fragment_fetch, TIER_HEDGE_INSTRUCTION

ACTORS_DIR = Path("resources/actors")


@pytest.fixture(scope="module")
def specs():
    return load_actor_specs(ACTORS_DIR)


def _spec(specs, name: str):
    for s in specs:
        if s.first_name.lower() == name.lower() or s.nickname.lower() == name.lower():
            return s
    raise ValueError(f"Actor '{name}' not found")


# ---------------------------------------------------------------------------
# Standard query — always-injected fragments
# ---------------------------------------------------------------------------

class TestAlwaysInjected:

    def test_base_always_present(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "base" in categories

    def test_voice_always_present(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "voice" in categories

    def test_limits_always_present(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "limits" in categories


# ---------------------------------------------------------------------------
# Domain match
# ---------------------------------------------------------------------------

class TestDomainMatch:

    def test_domain_injected_on_keyword_match(self, specs):
        # "assassination" is in Wale's domain_keywords
        result = fragment_fetch(_spec(specs, "Wale"), "should we proceed with the assassination?", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "domain" in categories

    def test_domain_not_injected_on_no_match(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "what's the weather like?", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "domain" not in categories


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

class TestRelationships:

    def test_relationships_injected_when_actor_present(self, specs):
        result = fragment_fetch(
            _spec(specs, "Wale"), "anything", TierConfidence.FULL,
            other_actor_names=["Jonathan Pratt"]
        )
        categories = [f.category for f in result.fragments]
        assert "relationships" in categories

    def test_relationships_not_injected_when_no_other_actor(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "relationships" not in categories


# ---------------------------------------------------------------------------
# Tier hedge
# ---------------------------------------------------------------------------

class TestTierHedge:

    def test_hedge_instruction_injected_when_hedged(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.HEDGED)
        categories = [f.category for f in result.fragments]
        assert "tier_hedge" in categories

    def test_hedge_instruction_content(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.HEDGED)
        hedge = next(f for f in result.fragments if f.category == "tier_hedge")
        assert hedge.content == TIER_HEDGE_INSTRUCTION

    def test_no_hedge_when_full_confidence(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.FULL)
        categories = [f.category for f in result.fragments]
        assert "tier_hedge" not in categories


# ---------------------------------------------------------------------------
# Spectator path
# ---------------------------------------------------------------------------

class TestSpectatorPath:

    def test_spectator_only_returns_spectator_fragment(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "", TierConfidence.FULL, spectator_only=True)
        categories = [f.category for f in result.fragments]
        assert categories == ["spectator"]

    def test_spectator_excludes_voice_and_limits(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "", TierConfidence.FULL, spectator_only=True)
        categories = [f.category for f in result.fragments]
        assert "voice" not in categories
        assert "limits" not in categories


# ---------------------------------------------------------------------------
# assembled() helper
# ---------------------------------------------------------------------------

class TestAssembled:

    def test_assembled_returns_non_empty_string(self, specs):
        result = fragment_fetch(_spec(specs, "Wale"), "anything", TierConfidence.FULL)
        text = result.assembled()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_unknown_fragment_category_skipped_gracefully(self, specs):
        # Fragment fetch should not crash if a category is missing from persona.md
        result = fragment_fetch(_spec(specs, "CODEX"), "anything", TierConfidence.FULL)
        assert result is not None
