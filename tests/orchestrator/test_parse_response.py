"""
tests/orchestrator/test_parse_response.py

Unit tests for src/orchestrator/parse_response.py.
"""

import pytest
from src.orchestrator.llm_call import LLMResult, _FALLBACK_RESPONSE
from src.orchestrator.parse_response import parse_response


def _result(raw: str) -> LLMResult:
    return LLMResult(raw=raw, flow_type="standard", success=True)


# ---------------------------------------------------------------------------
# Well-formed output
# ---------------------------------------------------------------------------

class TestWellFormed:

    def test_all_blocks_extracted(self):
        raw = "[THOUGHT] domain check\n[ACTION] FETCH nations WHERE region='asia'\n[CHAT] Lin: We have leverage."
        parsed = parse_response(_result(raw))
        assert parsed.thought == "domain check"
        assert parsed.action == "FETCH nations WHERE region='asia'"
        assert parsed.chat == "Lin: We have leverage."
        assert parsed.action_valid is True
        assert parsed.fallback_used is False

    def test_case_insensitive_block_tags(self):
        raw = "[thought] ok\n[chat] Wale: Na so e be."
        parsed = parse_response(_result(raw))
        assert parsed.thought == "ok"
        assert parsed.chat == "Wale: Na so e be."


# ---------------------------------------------------------------------------
# Missing blocks
# ---------------------------------------------------------------------------

class TestMissingBlocks:

    def test_missing_chat_uses_fallback(self):
        raw = "[THOUGHT] ok\n[ACTION] FETCH something"
        parsed = parse_response(_result(raw))
        assert parsed.chat == _FALLBACK_RESPONSE
        assert parsed.fallback_used is True

    def test_missing_thought_continues(self):
        raw = "[ACTION] FETCH x\n[CHAT] Lin: noted."
        parsed = parse_response(_result(raw))
        assert parsed.thought is None
        assert parsed.chat == "Lin: noted."
        assert parsed.fallback_used is False

    def test_missing_action_continues(self):
        raw = "[THOUGHT] ok\n[CHAT] Jonny: boost budget won't support that."
        parsed = parse_response(_result(raw))
        assert parsed.action is None
        assert parsed.chat == "Jonny: boost budget won't support that."


# ---------------------------------------------------------------------------
# No block tags
# ---------------------------------------------------------------------------

class TestNoBlocks:

    def test_no_blocks_treated_as_chat(self):
        raw = "Wale just said something without any tags."
        parsed = parse_response(_result(raw))
        assert parsed.chat == raw
        assert parsed.thought is None
        assert parsed.action is None
        assert parsed.fallback_used is False

    def test_empty_output_uses_fallback(self):
        parsed = parse_response(_result(""))
        assert parsed.chat == _FALLBACK_RESPONSE
        assert parsed.fallback_used is True


# ---------------------------------------------------------------------------
# Malformed ACTION
# ---------------------------------------------------------------------------

class TestMalformedAction:

    def test_malformed_action_rejected(self):
        raw = "[THOUGHT] ok\n[ACTION] DO SOMETHING ILLEGAL\n[CHAT] Lin: noted."
        parsed = parse_response(_result(raw))
        assert parsed.action is None
        assert parsed.action_valid is False
        assert parsed.chat == "Lin: noted."

    def test_valid_fetch_action_accepted(self):
        raw = "[THOUGHT] ok\n[ACTION] FETCH dialogue WHERE topic='orbital'\n[CHAT] Jonny: here."
        parsed = parse_response(_result(raw))
        assert parsed.action_valid is True

    def test_valid_update_action_accepted(self):
        raw = "[THOUGHT] ok\n[ACTION] UPDATE priorities SET focus='military'\n[CHAT] Katya: done."
        parsed = parse_response(_result(raw))
        assert parsed.action_valid is True
