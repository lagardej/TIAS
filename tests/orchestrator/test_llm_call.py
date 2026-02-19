"""
tests/orchestrator/test_llm_call.py

Unit tests for src/orchestrator/llm_call.py.
All tests mock the requests.post call — no live LLM required.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.orchestrator.prompt_assemble import AssembledPrompt
from src.orchestrator.llm_call import LLM_CONFIGS, LLMResult, _FALLBACK_RESPONSE, llm_call

DUMMY_PROMPT = AssembledPrompt(system="System block.", user="User block.")


def _mock_response(content: str, status: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock.raise_for_status = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# Config correctness
# ---------------------------------------------------------------------------

class TestLLMConfigs:

    @pytest.mark.parametrize("flow_type,max_tokens,temperature", [
        ("standard",         150, 0.7),
        ("debate_turn",      150, 0.8),
        ("debate_interrupt",  75, 0.5),
        ("spectator",         50, 0.5),
    ])
    def test_config_values(self, flow_type, max_tokens, temperature):
        assert LLM_CONFIGS[flow_type]["max_tokens"] == max_tokens
        assert LLM_CONFIGS[flow_type]["temperature"] == temperature


# ---------------------------------------------------------------------------
# Successful calls
# ---------------------------------------------------------------------------

class TestSuccessfulCall:

    def test_standard_flow(self):
        with patch("requests.post", return_value=_mock_response("Wale: Na so e be.")) as mock_post:
            result = llm_call(DUMMY_PROMPT, "standard", backend_url="http://localhost:5001")
        assert result.success is True
        assert result.raw == "Wale: Na so e be."
        payload = mock_post.call_args.kwargs["json"]
        assert payload["max_tokens"] == 150
        assert payload["temperature"] == 0.7

    def test_debate_turn_config(self):
        with patch("requests.post", return_value=_mock_response("Lin: We have leverage.")) as mock_post:
            result = llm_call(DUMMY_PROMPT, "debate_turn", backend_url="http://localhost:5001")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["max_tokens"] == 150
        assert payload["temperature"] == 0.8

    def test_debate_interrupt_config(self):
        with patch("requests.post", return_value=_mock_response("Lin: Decide.")) as mock_post:
            result = llm_call(DUMMY_PROMPT, "debate_interrupt", backend_url="http://localhost:5001")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["max_tokens"] == 75
        assert payload["temperature"] == 0.5

    def test_spectator_config(self):
        with patch("requests.post", return_value=_mock_response("[Wale looks at the ceiling.]")) as mock_post:
            result = llm_call(DUMMY_PROMPT, "spectator", backend_url="http://localhost:5001")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["max_tokens"] == 50
        assert payload["temperature"] == 0.5


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

class TestFailureModes:

    def test_timeout_returns_fallback(self):
        with patch("requests.post", side_effect=requests.exceptions.Timeout):
            result = llm_call(DUMMY_PROMPT, "standard", backend_url="http://localhost:5001")
        assert result.success is False
        assert result.raw == _FALLBACK_RESPONSE
        assert result.error == "timeout"

    def test_request_exception_returns_fallback(self):
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
            result = llm_call(DUMMY_PROMPT, "standard", backend_url="http://localhost:5001")
        assert result.success is False
        assert result.raw == _FALLBACK_RESPONSE

    def test_empty_response_returns_fallback(self):
        with patch("requests.post", return_value=_mock_response("")):
            result = llm_call(DUMMY_PROMPT, "standard", backend_url="http://localhost:5001")
        assert result.success is False
        assert result.raw == _FALLBACK_RESPONSE
        assert result.error == "empty response"

    def test_unknown_flow_type_falls_back_to_standard_config(self):
        with patch("requests.post", return_value=_mock_response("response")) as mock_post:
            result = llm_call(DUMMY_PROMPT, "nonexistent_flow", backend_url="http://localhost:5001")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["max_tokens"] == LLM_CONFIGS["standard"]["max_tokens"]
