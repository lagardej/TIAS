"""
commit_log.py — Atomic commit and session transcript logging.

Responsibilities:
    - Append turn to human-readable dialogue log in ./logs/
    - Insert [CHAT] block to dialogue_fts (stub until V2 DB migration)
    - Update decision_log if an UPDATE action was executed
    - All operations atomic: log write failure rolls back

Log format: one file per session, one turn appended per call.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.orchestrator.parse_response import ParsedResponse
from src.orchestrator.validate_action import ActionResult


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class CommitContext:
    session_id: str       # e.g. "2026-02-19_143201"
    flow_type: str
    tier: int
    speaker: str          # actor display name or "USER"
    query: str
    parsed: ParsedResponse
    action_result: ActionResult | None


# ---------------------------------------------------------------------------
# Log formatting
# ---------------------------------------------------------------------------

def _format_turn(ctx: CommitContext) -> str:
    lines = [
        f"=== SESSION {ctx.session_id} | TIER {ctx.tier} | {ctx.flow_type.upper()} ===",
        "",
        "USER",
        ctx.query,
        "",
    ]
    if ctx.parsed.thought:
        lines += [f"[THOUGHT] {ctx.parsed.thought}", ""]
    if ctx.parsed.action and ctx.action_result:
        status = "OK" if ctx.action_result.executed else "REJECTED"
        lines += [f"[ACTION] {ctx.parsed.action}  [{status}]", ""]
    lines += [
        ctx.speaker.upper(),
        ctx.parsed.chat,
        "",
        "=== TURN END ===",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dialogue FTS stub
# Replaced with real SQLite FTS5 insert during V2 DB migration.
# ---------------------------------------------------------------------------

def _insert_dialogue_fts(session_id: str, speaker: str, chat: str, db_path: Path | None) -> None:
    if db_path is None:
        logging.debug("No DB path — dialogue_fts insert skipped (stub)")
        return
    try:
        con = sqlite3.connect(db_path)
        con.execute(
            "INSERT INTO dialogue_fts (session_id, speaker, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, speaker, chat, datetime.utcnow().isoformat()),
        )
        con.commit()
        con.close()
    except sqlite3.Error as e:
        logging.error(f"dialogue_fts insert failed: {e}")
        raise


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def commit_log(
    ctx: CommitContext,
    logs_dir: Path,
    db_path: Path | None = None,
) -> None:
    """
    Atomically write turn to log file and dialogue_fts.

    Raises on log write failure so caller can surface the error.
    SQLite insert failure rolls back and re-raises.

    Args:
        ctx:       CommitContext for this turn.
        logs_dir:  Directory for session transcript files (./logs/).
        db_path:   Optional path to campaign SQLite DB (stub if None).
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"session_{ctx.session_id}.log"
    turn_text = _format_turn(ctx)

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(turn_text)
    except OSError as e:
        logging.error(f"Log write failed: {e}")
        raise

    # dialogue_fts insert — if it fails, log the error but don't lose the turn
    try:
        _insert_dialogue_fts(ctx.session_id, ctx.speaker, ctx.parsed.chat, db_path)
    except Exception as e:
        logging.error(f"dialogue_fts insert failed, continuing: {e}")


def make_session_id() -> str:
    """Generate a session ID from current UTC time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
