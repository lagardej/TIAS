"""
tests/test_identify_actor.py

Unit tests for src/orchestrator/identify_actor.py.

Explicit routing tests use real actor specs from resources/actors/.
Implicit routing tests mock _implicit_match to avoid loading the embedding model.
Ambiguous Kim test uses fixture specs from tests/fixtures/actors/.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.orchestrator.identify_actor import (
    AdvisorRole,
    FlowType,
    IdentifyResult,
    identify_actor,
    load_actor_specs,
)

ACTORS_DIR   = Path("resources/actors")
FIXTURES_DIR = Path("tests/fixtures/actors")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_specs():
    """Real actor specs — used for all explicit routing tests."""
    return load_actor_specs(ACTORS_DIR)


@pytest.fixture(scope="module")
def ambiguous_specs(real_specs):
    """
    Real specs + fixture Kim actor.
    Jun-ho has family_name 'Kim' — fixture adds a second Kim to force ambiguity.
    """
    fixture_specs = load_actor_specs(FIXTURES_DIR)
    return real_specs + fixture_specs


# ---------------------------------------------------------------------------
# Explicit routing
# ---------------------------------------------------------------------------

class TestExplicitRouting:

    def test_first_name_match(self, real_specs):
        result = identify_actor("Jonny, what's our boost budget?", real_specs)
        assert result.flow_type == FlowType.STANDARD
        assert len(result.actors) == 1
        assert result.actors[0].spec.first_name == "Jonathan"
        assert result.actors[0].role == AdvisorRole.MAIN

    def test_nickname_match(self, real_specs):
        result = identify_actor("Ankledeep, are you available?", real_specs)
        assert result.flow_type == FlowType.STANDARD
        assert len(result.actors) == 1
        assert result.actors[0].spec.nickname == "Ankledeep"
        assert result.actors[0].role == AdvisorRole.MAIN

    def test_ambiguous_two_kims(self, ambiguous_specs):
        result = identify_actor("Kim, what's your take?", ambiguous_specs)
        assert result.flow_type == FlowType.AMBIGUOUS
        assert len(result.actors) == 2
        assert result.stage_note is not None

    def test_explicit_no_match_falls_through_to_implicit(self, real_specs):
        # "Zaphod" matches no actor — falls through to implicit path
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=[]):
            result = identify_actor("Zaphod, what's your take?", real_specs)
        assert result.flow_type == FlowType.TOO_VAGUE


# ---------------------------------------------------------------------------
# Implicit routing
# ---------------------------------------------------------------------------

class TestImplicitRouting:

    def test_too_vague(self, real_specs):
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=[]):
            result = identify_actor("Hmm.", real_specs)
        assert result.flow_type == FlowType.TOO_VAGUE
        assert result.stage_note is not None

    def test_too_broad(self, real_specs):
        fake = [(real_specs[0], 0.80), (real_specs[1], 0.75), (real_specs[2], 0.71)]
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=fake):
            result = identify_actor("What do you all think?", real_specs)
        assert result.flow_type == FlowType.TOO_BROAD
        assert result.stage_note is not None

    def test_single_main(self, real_specs):
        fake = [(real_specs[0], 0.80)]
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=fake):
            result = identify_actor("What should we do in Southeast Asia?", real_specs)
        assert result.flow_type == FlowType.STANDARD
        assert len(result.actors) == 1
        assert result.actors[0].role == AdvisorRole.MAIN

    def test_main_and_support(self, real_specs):
        fake = [(real_specs[0], 0.80), (real_specs[1], 0.45)]
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=fake):
            result = identify_actor("Should we expand orbital presence?", real_specs)
        assert result.flow_type == FlowType.STANDARD
        assert result.actors[0].role == AdvisorRole.MAIN
        assert result.actors[1].role == AdvisorRole.SUPPORT

    def test_two_mains_triggers_debate(self, real_specs):
        fake = [(real_specs[0], 0.80), (real_specs[1], 0.75)]
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=fake):
            result = identify_actor("Should we hit the shipyard?", real_specs)
        assert result.flow_type == FlowType.DEBATE
        assert len(result.actors) == 2
        assert all(a.role == AdvisorRole.MAIN for a in result.actors)

    def test_two_supports_triggers_debate(self, real_specs):
        # 2 supports + 0 main → low-confidence debate, user arbitrates
        fake = [(real_specs[0], 0.50), (real_specs[1], 0.40)]
        with patch("src.orchestrator.identify_actor._implicit_match", return_value=fake):
            result = identify_actor("Some vague question?", real_specs)
        assert result.flow_type == FlowType.DEBATE
        assert result.actors[0].role == AdvisorRole.SUPPORT
        assert result.actors[1].role == AdvisorRole.SUPPORT
