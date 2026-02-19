"""
parse_response.py — Extract [THOUGHT], [ACTION], and [CHAT] blocks from LLM output.

Failure handling:
    Missing [CHAT]       → canned fallback, log error
    Missing [THOUGHT]    → continue, log warning
    Missing [ACTION]     → continue, skip validate_action
    No blocks at all     → treat full output as [CHAT], flag in log
    Malformed [ACTION]   → reject action, log, [CHAT] still returned
"""

import logging
import re
from dataclasses import dataclass

from src.orchestrator.llm_call import LLMResult, _FALLBACK_RESPONSE


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ParsedResponse:
    thought: str | None
    action: str | None
    chat: str
    action_valid: bool   # False if action block present but malformed
    fallback_used: bool  # True if [CHAT] was missing or output had no blocks


# ---------------------------------------------------------------------------
# Block extraction
# ---------------------------------------------------------------------------

_BLOCK_PATTERN = re.compile(
    r"\[(THOUGHT|ACTION|CHAT)\](.*?)(?=\[(?:THOUGHT|ACTION|CHAT)\]|\Z)",
    re.DOTALL | re.IGNORECASE,
)

# Basic ACTION validation: must start with FETCH or UPDATE followed by content
_ACTION_VALID_PATTERN = re.compile(r"^\s*(FETCH|UPDATE)\s+\S+", re.IGNORECASE)


def parse_response(result: LLMResult) -> ParsedResponse:
    """
    Parse raw LLM output into structured blocks.
    Always returns a ParsedResponse with a non-empty chat field.
    """
    raw = result.raw.strip()
    blocks = {m.group(1).upper(): m.group(2).strip() for m in _BLOCK_PATTERN.finditer(raw)}

    # No blocks found — treat entire output as CHAT
    if not blocks:
        logging.warning("LLM output contained no [BLOCK] tags — treating as [CHAT]")
        return ParsedResponse(
            thought=None,
            action=None,
            chat=raw or _FALLBACK_RESPONSE,
            action_valid=False,
            fallback_used=not bool(raw),
        )

    thought = blocks.get("THOUGHT")
    action_raw = blocks.get("ACTION")
    chat = blocks.get("CHAT")

    if not thought:
        logging.warning("LLM output missing [THOUGHT] block")

    if not action_raw:
        logging.debug("No [ACTION] block in response")

    # Validate action if present
    action_valid = False
    if action_raw:
        if _ACTION_VALID_PATTERN.match(action_raw):
            action_valid = True
        else:
            logging.warning(f"Malformed [ACTION] block rejected: {action_raw!r}")
            action_raw = None

    # Missing CHAT — use fallback
    if not chat:
        logging.error("LLM output missing [CHAT] block — using fallback")
        return ParsedResponse(
            thought=thought,
            action=action_raw,
            chat=_FALLBACK_RESPONSE,
            action_valid=action_valid,
            fallback_used=True,
        )

    return ParsedResponse(
        thought=thought,
        action=action_raw,
        chat=chat,
        action_valid=action_valid,
        fallback_used=False,
    )
