"""
display.py — Format parsed response for terminal output.

No LLM call. Pure formatting layer.

Flow types:
    standard / debate_turn   → actor name + chat block
    debate_interrupt         → actor name + chat block + decision prompt
    spectator                → stage direction formatting, no name prefix
    error / fallback         → system message, distinct formatting
"""

from src.orchestrator.parse_response import ParsedResponse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DECISION_PROMPT = "— your decision."
_SYSTEM_PREFIX  = "[SYSTEM]"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def display(parsed: ParsedResponse, flow_type: str, speaker: str | None = None) -> str:
    """
    Format a parsed response for terminal output.

    Args:
        parsed:     ParsedResponse from parse_response().
        flow_type:  One of: standard, debate_turn, debate_interrupt, spectator, error.
        speaker:    Actor display name (None for spectator/error flows).

    Returns:
        Formatted string ready for print().
    """
    chat = parsed.chat.strip()

    if not chat:
        return ""

    if flow_type == "spectator":
        return chat

    if flow_type == "error":
        return f"{_SYSTEM_PREFIX} {chat}"

    if flow_type == "debate_interrupt":
        prefix = f"{speaker.upper()}: " if speaker else ""
        return f"{prefix}{chat}\n\n{DECISION_PROMPT}"

    # standard / debate_turn
    prefix = f"{speaker.upper()}: " if speaker else ""
    return f"{prefix}{chat}"
