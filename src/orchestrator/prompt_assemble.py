"""
prompt_assemble.py — Assemble the final prompt from fragments and game state.

Assembly order (matches KV cache strategy — system block never changes):
    [system]    global rules — static, loaded once
    [actor]     assembled fragments: base → voice → domain → relationships → limits → tier_hedge
    [context]   CODEX gamestate report (line-budgeted) or LLM-generated stage direction
    [history]   last N turns from dialogue history
    [query]     user input

The system block must remain byte-identical across turns to preserve KV cache.
Any modification to system.txt invalidates the cache — log a warning if it changes.
"""

import hashlib
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from src.orchestrator.fragment_fetch import FetchResult


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class HistoryTurn:
    role: str       # "user" or "advisor"
    speaker: str    # display name or "User"
    content: str


@dataclass
class AssembledPrompt:
    system: str
    user: str       # everything after system — sent as the user turn in OpenAI format


# ---------------------------------------------------------------------------
# System block (KV cache anchor)
# ---------------------------------------------------------------------------

_system_hash: str | None = None


def load_system_prompt(system_path: Path) -> str:
    """
    Load system.txt. Warn if content has changed since last load
    (indicates KV cache invalidation).
    """
    global _system_hash
    content = system_path.read_text(encoding="utf-8").strip()
    current_hash = hashlib.md5(content.encode()).hexdigest()

    if _system_hash is None:
        _system_hash = current_hash
    elif _system_hash != current_hash:
        logging.warning(
            "system.txt has changed since last load — KV cache invalidated. "
            "Restart session to restore cache efficiency."
        )
        _system_hash = current_hash

    return content


# ---------------------------------------------------------------------------
# CODEX report handling
# ---------------------------------------------------------------------------

def _load_gamestate(campaigns_dir: Path) -> str:
    """
    Load gamestate from savegame.db if present, else fall back to gamestate_*.txt files.
    """
    db_path = campaigns_dir / "savegame.db"
    if db_path.exists():
        from src.db.query import build_codex_report
        return build_codex_report(db_path)
    # Legacy fallback
    files = sorted(campaigns_dir.glob("gamestate_*.txt"))
    parts = [f.read_text(encoding="utf-8").strip() for f in files if f.stat().st_size > 0]
    return "\n\n".join(parts)


def _codex_report_or_stage_direction(
    campaigns_dir: Path,
    codex_spec_path: Path,
) -> str:
    """
    Return CODEX report if under line budget, otherwise return a placeholder
    instructing the LLM to generate an in-character stage direction.

    The stage direction examples in codex/spec.toml are tone reference only —
    the LLM generates the actual line.
    """
    with open(codex_spec_path, "rb") as f:
        codex_data = tomllib.load(f)

    line_budget: int = codex_data.get("report_line_budget", 40)
    logging.debug(f"CODEX spec path: {codex_spec_path} | line_budget: {line_budget}")
    report = _load_gamestate(campaigns_dir)

    if not report:
        return "[No game state data available. CODEX is silent.]"

    line_count = report.count("\n") + 1
    if line_count <= line_budget:
        return report

    # Over budget — instruct LLM to generate stage direction
    examples = "\n".join([
        "[CODEX floods the room with figures. Lin is already three pages ahead. Everyone else has stopped pretending.]",
        "[The report continues. It has been continuing for some time. Wale has found something else to look at.]",
        "[CODEX appends a seventh appendix. The council's attention has quietly left the building.]",
    ])
    return (
        f"[CODEX REPORT EXCEEDS LINE BUDGET ({line_count} lines > {line_budget})]\n"
        f"Generate a single in-character stage direction conveying information overload.\n"
        f"Tone reference (do not reproduce these exactly):\n{examples}"
    )


# ---------------------------------------------------------------------------
# History block
# ---------------------------------------------------------------------------

def _format_history(history: list[HistoryTurn]) -> str:
    if not history:
        return ""
    lines = []
    for turn in history:
        prefix = turn.speaker.upper() if turn.role == "advisor" else "USER"
        lines.append(f"{prefix}: {turn.content}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def prompt_assemble(
    fetch_results: list[FetchResult],
    query: str,
    system_path: Path,
    campaigns_dir: Path,
    codex_spec_path: Path,
    history: list[HistoryTurn] | None = None,
    tier: int = 1,
) -> AssembledPrompt:
    """
    Assemble the final prompt from all components.

    Args:
        fetch_results:    One FetchResult per active actor (1 or 2).
        query:            Raw user input.
        system_path:      Path to resources/prompts/system.txt.
        campaigns_dir:    Path to campaigns/{faction}/{date}/ for gamestate files.
        codex_spec_path:  Path to resources/actors/codex/spec.toml.
        history:          Recent dialogue turns (soft/hard capped upstream).
        tier:             Current campaign tier (injected into system prompt).
    """
    # System block — static, {tier} substituted
    system_raw = load_system_prompt(system_path)
    system = system_raw.replace("{tier}", str(tier))

    # Actor fragments
    actor_blocks = []
    for fetch in fetch_results:
        actor_blocks.append(fetch.assembled())
    actor_section = "\n\n---\n\n".join(actor_blocks)

    # Context (CODEX gamestate) — only injected when CODEX is active
    is_codex_query = any(
        fr.actor.first_name.lower() == "codex" for fr in fetch_results
    )
    context_section = _codex_report_or_stage_direction(campaigns_dir, codex_spec_path) if is_codex_query else ""

    # History
    history_section = _format_history(history or [])

    # Assemble user turn
    parts = []
    parts.append("IMPORTANT: Your entire response must use ONLY these tags:\n[THOUGHT] your reasoning\n[CHAT] in-character response\nDo NOT write anything outside these tags.")
    if actor_section:
        parts.append(f"## ADVISOR CONTEXT\n\n{actor_section}")
    if context_section:
        parts.append(f"## GAME STATE\n\n{context_section}")
    if history_section:
        parts.append(f"## RECENT HISTORY\n\n{history_section}")
    parts.append(f"## QUERY\n\n{query}")
    parts.append("Respond now using [THOUGHT] and [CHAT] tags only.")

    user_turn = "\n\n".join(parts)

    return AssembledPrompt(system=system, user=user_turn)
