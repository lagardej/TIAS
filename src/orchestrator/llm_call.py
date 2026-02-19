"""
llm_call.py — Send assembled prompt to LLM backend.

Uses OpenAI-compatible API (KoboldCpp, LM Studio, Ollama, etc.).
Per-flow-type config controls max_tokens and temperature.
Backend URL loaded from environment — no hardcoded addresses.
"""

import logging
import os
from dataclasses import dataclass

import requests

from src.orchestrator.prompt_assemble import AssembledPrompt


# ---------------------------------------------------------------------------
# Per-flow-type LLM config
# Initial values — tune after measurement.
# ---------------------------------------------------------------------------

LLM_CONFIGS: dict[str, dict] = {
    "standard":          {"max_tokens": 150, "temperature": 0.7},
    "codex":             {"max_tokens": 400, "temperature": 0.2},
    "debate_turn":       {"max_tokens": 150, "temperature": 0.8},
    "debate_interrupt":  {"max_tokens":  75, "temperature": 0.5},
    "spectator":         {"max_tokens":  50, "temperature": 0.5},
}

_FALLBACK_RESPONSE = "[The council is silent. Something has gone wrong.]"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class LLMResult:
    raw: str
    flow_type: str
    success: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def llm_call(prompt: AssembledPrompt, flow_type: str, backend_url: str | None = None) -> LLMResult:
    """
    Send prompt to LLM backend. Returns LLMResult with raw output.

    Args:
        prompt:       AssembledPrompt from prompt_assemble().
        flow_type:    One of: standard, debate_turn, debate_interrupt, spectator.
        backend_url:  Override backend URL (defaults to BACKEND_URL env var).
    """
    url = _resolve_url(backend_url)
    config = LLM_CONFIGS.get(flow_type, LLM_CONFIGS["standard"])

    if flow_type not in LLM_CONFIGS:
        logging.warning(f"Unknown flow_type '{flow_type}', falling back to 'standard' config")

    payload = {
        "model": "koboldcpp",
        "messages": [
            {"role": "system", "content": prompt.system},
            {"role": "user",   "content": prompt.user},
        ],
        "max_tokens":  config["max_tokens"],
        "temperature": config["temperature"],
    }

    try:
        response = requests.post(
            f"{url}/v1/chat/completions",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()

        if not raw:
            logging.warning("LLM returned empty response")
            return LLMResult(raw=_FALLBACK_RESPONSE, flow_type=flow_type, success=False, error="empty response")

        return LLMResult(raw=raw, flow_type=flow_type, success=True)

    except requests.exceptions.Timeout:
        logging.error(f"LLM timeout after 120s (flow_type={flow_type})")
        return LLMResult(raw=_FALLBACK_RESPONSE, flow_type=flow_type, success=False, error="timeout")

    except requests.exceptions.RequestException as e:
        logging.error(f"LLM request failed: {e}")
        return LLMResult(raw=_FALLBACK_RESPONSE, flow_type=flow_type, success=False, error=str(e))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_url(override: str | None) -> str:
    """Resolve backend URL from override, env var, or default."""
    if override:
        return override.rstrip("/")
    env_url = os.environ.get("BACKEND_URL", "http://localhost:5001")
    return env_url.rstrip("/")
