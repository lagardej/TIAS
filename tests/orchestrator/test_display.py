"""
tests/orchestrator/test_display.py

Unit tests for src/orchestrator/display.py.
"""

import pytest
from src.orchestrator.parse_response import ParsedResponse
from src.orchestrator.display import display, DECISION_PROMPT, _SYSTEM_PREFIX


def _parsed(chat: str) -> ParsedResponse:
    return ParsedResponse(
        thought=None, action=None, chat=chat,
        action_valid=False, fallback_used=False
    )


# ---------------------------------------------------------------------------
# Standard / debate_turn
# ---------------------------------------------------------------------------

class TestStandard:

    def test_speaker_prefixed(self):
        result = display(_parsed("Na so e be."), "standard", speaker="Wale Oluwaseun")
        assert result == "WALE OLUWASEUN: Na so e be."

    def test_debate_turn_same_as_standard(self):
        result = display(_parsed("We have leverage."), "debate_turn", speaker="Lin Mei-hua")
        assert result == "LIN MEI-HUA: We have leverage."

    def test_no_speaker_no_prefix(self):
        result = display(_parsed("Something."), "standard", speaker=None)
        assert result == "Something."


# ---------------------------------------------------------------------------
# Debate interrupt
# ---------------------------------------------------------------------------

class TestDebateInterrupt:

    def test_includes_decision_prompt(self):
        result = display(_parsed("Decide."), "debate_interrupt", speaker="Lin Mei-hua")
        assert DECISION_PROMPT in result

    def test_speaker_present(self):
        result = display(_parsed("Decide."), "debate_interrupt", speaker="Lin Mei-hua")
        assert "LIN MEI-HUA" in result

    def test_decision_prompt_after_chat(self):
        result = display(_parsed("Decide."), "debate_interrupt", speaker="Lin Mei-hua")
        assert result.index("Decide.") < result.index(DECISION_PROMPT)


# ---------------------------------------------------------------------------
# Spectator
# ---------------------------------------------------------------------------

class TestSpectator:

    def test_no_name_prefix(self):
        result = display(_parsed("[Wale looks at the ceiling.]"), "spectator")
        assert not result.startswith("[SYSTEM]")
        assert "WALE" not in result.split("]")[0]

    def test_chat_returned_as_is(self):
        result = display(_parsed("[Wale looks at the ceiling.]"), "spectator")
        assert result == "[Wale looks at the ceiling.]"


# ---------------------------------------------------------------------------
# Error / fallback
# ---------------------------------------------------------------------------

class TestError:

    def test_system_prefix(self):
        result = display(_parsed("Something went wrong."), "error")
        assert result.startswith(_SYSTEM_PREFIX)

    def test_distinct_from_standard(self):
        std = display(_parsed("msg"), "standard", speaker="Wale Oluwaseun")
        err = display(_parsed("msg"), "error")
        assert std != err


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_chat_returns_empty(self):
        result = display(_parsed(""), "standard", speaker="Wale Oluwaseun")
        assert result == ""

    def test_whitespace_only_chat_returns_empty(self):
        result = display(_parsed("   "), "standard", speaker="Wale Oluwaseun")
        assert result == ""
