"""
tests/orchestrator/test_prompt_assemble.py

Unit tests for src/orchestrator/prompt_assemble.py.
Uses real system.txt and actor specs. Mocks gamestate files where needed.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.orchestrator.identify_actor import load_actor_specs
from src.orchestrator.tier_check import TierConfidence
from src.orchestrator.fragment_fetch import fragment_fetch
from src.orchestrator.prompt_assemble import (
    prompt_assemble,
    load_system_prompt,
    HistoryTurn,
    AssembledPrompt,
)

ACTORS_DIR    = Path("resources/actors")
SYSTEM_PATH   = Path("resources/prompts/system.txt")
CAMPAIGNS_DIR = Path("campaigns/resist/2027-08-01")
CODEX_SPEC    = Path("resources/actors/codex/spec.toml")


@pytest.fixture(scope="module")
def specs():
    return load_actor_specs(ACTORS_DIR)


def _spec(specs, name: str):
    for s in specs:
        if s.first_name.lower() == name.lower() or s.nickname.lower() == name.lower():
            return s
    raise ValueError(f"Actor '{name}' not found")


def _fetch(specs, name: str, query: str = "anything", confidence: TierConfidence = TierConfidence.FULL):
    return fragment_fetch(_spec(specs, name), query, confidence)


# ---------------------------------------------------------------------------
# System block
# ---------------------------------------------------------------------------

class TestSystemBlock:

    def test_tier_substituted(self, specs):
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "test query",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC, tier=2
        )
        assert "{tier}" not in result.system
        assert "2" in result.system

    def test_system_hash_warning_on_change(self, tmp_path):
        # Reset module-level hash to ensure test isolation
        import src.orchestrator.prompt_assemble as pa
        pa._system_hash = None

        sys_file = tmp_path / "system.txt"
        sys_file.write_text("Version 1", encoding="utf-8")
        load_system_prompt(sys_file)
        sys_file.write_text("Version 2 - modified", encoding="utf-8")
        import logging
        with patch.object(logging, "warning") as mock_warn:
            load_system_prompt(sys_file)
            mock_warn.assert_called_once()
            assert "KV cache" in mock_warn.call_args[0][0]

        # Restore to None so subsequent tests are unaffected
        pa._system_hash = None


# ---------------------------------------------------------------------------
# Actor fragments in assembled prompt
# ---------------------------------------------------------------------------

class TestActorSection:

    def test_actor_context_present(self, specs):
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "test",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC
        )
        assert "ADVISOR CONTEXT" in result.user

    def test_two_actors_both_present(self, specs):
        fetches = [_fetch(specs, "Wale"), _fetch(specs, "Jonny")]
        result = prompt_assemble(fetches, "test", SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC)
        assert "Wale" in result.user
        assert "Jonathan" in result.user


# ---------------------------------------------------------------------------
# CODEX report / gamestate
# ---------------------------------------------------------------------------

class TestGameState:

    def test_gamestate_under_budget_included(self, specs):
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "test",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC
        )
        assert "GAME STATE" in result.user

    def test_gamestate_over_budget_returns_stage_direction(self, specs, tmp_path):
        # Write a gamestate file exceeding 40 lines
        gen_dir = tmp_path / "campaigns"
        gen_dir.mkdir()
        fat_report = "\n".join([f"Line {i}: data" for i in range(60)])
        (gen_dir / "gamestate_earth.txt").write_text(fat_report)

        result = prompt_assemble(
            [_fetch(specs, "Wale")], "test",
            SYSTEM_PATH, gen_dir, CODEX_SPEC
        )
        assert "EXCEEDS LINE BUDGET" in result.user or "stage direction" in result.user.lower()

    def test_no_gamestate_files_graceful(self, specs, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "test",
            SYSTEM_PATH, empty_dir, CODEX_SPEC
        )
        assert "CODEX is silent" in result.user


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class TestHistory:

    def test_no_history_first_turn(self, specs):
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "test",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC, history=[]
        )
        assert "RECENT HISTORY" not in result.user

    def test_history_present_when_provided(self, specs):
        history = [
            HistoryTurn(role="user", speaker="User", content="First question"),
            HistoryTurn(role="advisor", speaker="Wale Oluwaseun", content="First answer"),
        ]
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "second question",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC, history=history
        )
        assert "RECENT HISTORY" in result.user
        assert "First question" in result.user

    def test_two_actor_debate_history_includes_both(self, specs):
        history = [
            HistoryTurn(role="advisor", speaker="Wale Oluwaseun", content="My position."),
            HistoryTurn(role="advisor", speaker="Jonathan Pratt", content="My position."),
        ]
        fetches = [_fetch(specs, "Wale"), _fetch(specs, "Jonny")]
        result = prompt_assemble(
            fetches, "next question",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC, history=history
        )
        assert "Wale Oluwaseun".upper() in result.user
        assert "Jonathan Pratt".upper() in result.user


# ---------------------------------------------------------------------------
# Query always last
# ---------------------------------------------------------------------------

class TestQueryPosition:

    def test_query_present(self, specs):
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "my specific query",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC
        )
        assert "my specific query" in result.user

    def test_query_is_last_section(self, specs):
        result = prompt_assemble(
            [_fetch(specs, "Wale")], "my specific query",
            SYSTEM_PATH, CAMPAIGNS_DIR, CODEX_SPEC
        )
        assert result.user.endswith("my specific query")
