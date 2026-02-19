"""
validate_action.py — Validate and execute [ACTION] blocks before DB commit.

Actions:
    FETCH  → read-only, execute directly, no decision_log check
    UPDATE → check decision_log, execute if allowed, reject if denied

Decision log persists to campaigns/decision_log.json (JSON file, session-persistent).
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    executed: bool
    ruling: str          # "allowed", "denied", "fetch"
    rationale: str | None = None
    data: dict | None = None   # populated for FETCH results


# ---------------------------------------------------------------------------
# Decision log (JSON persistence)
# ---------------------------------------------------------------------------

def _load_log(log_path: Path) -> dict:
    if log_path.exists():
        return json.loads(log_path.read_text(encoding="utf-8"))
    return {}


def _save_log(log_path: Path, log: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _log_key(action: str) -> str:
    """Normalise action string to a stable key (lowercase, stripped)."""
    return action.strip().lower()


# ---------------------------------------------------------------------------
# Action parsing
# ---------------------------------------------------------------------------

def _parse_action(action: str) -> tuple[str, str]:
    """
    Split action into (verb, body).
    Returns ("unknown", action) if unrecognised.
    """
    parts = action.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0].upper(), parts[1]
    return "UNKNOWN", action


# ---------------------------------------------------------------------------
# Executor stubs
# Actual DB execution deferred to V2 DB migration.
# These stubs log intent and return success — replace with real queries later.
# ---------------------------------------------------------------------------

def _execute_fetch(body: str) -> ActionResult:
    logging.info(f"[ACTION] FETCH {body}")
    return ActionResult(executed=True, ruling="fetch", data={"stub": True})


def _execute_update(body: str) -> ActionResult:
    logging.info(f"[ACTION] UPDATE {body}")
    return ActionResult(executed=True, ruling="allowed", data={"stub": True})


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_action(action: str, log_path: Path) -> ActionResult:
    """
    Validate and execute a parsed action string.

    Args:
        action:    Raw action body from parse_response (already validated as FETCH/UPDATE).
        log_path:  Path to decision_log.json for the current campaign.
    """
    verb, body = _parse_action(action)

    if verb == "FETCH":
        return _execute_fetch(body)

    if verb == "UPDATE":
        log = _load_log(log_path)
        key = _log_key(action)
        prior = log.get(key)

        if prior == "denied":
            logging.warning(f"[ACTION] UPDATE denied by decision_log: {action!r}")
            return ActionResult(
                executed=False,
                ruling="denied",
                rationale=f"Prior ruling denied this action: {action}",
            )

        result = _execute_update(body)

        # Log new decision
        if not prior:
            log[key] = "allowed"
            _save_log(log_path, log)
            logging.info(f"[ACTION] New decision logged: {key!r}")

        return result

    logging.warning(f"[ACTION] Unknown verb '{verb}' — rejected")
    return ActionResult(executed=False, ruling="denied", rationale=f"Unknown action verb: {verb}")
