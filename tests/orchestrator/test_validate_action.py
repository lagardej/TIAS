"""
tests/orchestrator/test_validate_action.py

Unit tests for src/orchestrator/validate_action.py.
Uses tmp_path for decision_log.json isolation.
"""

import json
from pathlib import Path

import pytest

from src.orchestrator.validate_action import validate_action


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------

class TestFetch:

    def test_fetch_executes_without_log_check(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        result = validate_action("FETCH nations WHERE region='asia'", log_path)
        assert result.executed is True
        assert result.ruling == "fetch"
        # FETCH never writes to decision_log
        assert not log_path.exists()


# ---------------------------------------------------------------------------
# UPDATE — no prior ruling
# ---------------------------------------------------------------------------

class TestUpdateNoPrior:

    def test_update_executes_and_logs(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        result = validate_action("UPDATE priorities SET focus='military'", log_path)
        assert result.executed is True
        assert result.ruling == "allowed"
        assert log_path.exists()

    def test_update_writes_allowed_to_log(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        action = "UPDATE priorities SET focus='military'"
        validate_action(action, log_path)
        log = json.loads(log_path.read_text())
        assert any("allowed" == v for v in log.values())


# ---------------------------------------------------------------------------
# UPDATE — prior ruling allowed
# ---------------------------------------------------------------------------

class TestUpdatePriorAllowed:

    def test_prior_allowed_executes(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        action = "UPDATE priorities SET focus='military'"
        # First call logs it
        validate_action(action, log_path)
        # Second call uses prior
        result = validate_action(action, log_path)
        assert result.executed is True
        assert result.ruling == "allowed"


# ---------------------------------------------------------------------------
# UPDATE — prior ruling denied
# ---------------------------------------------------------------------------

class TestUpdatePriorDenied:

    def test_prior_denied_rejects(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        action = "UPDATE something forbidden"
        key = action.strip().lower()
        # Pre-seed log with denied ruling
        log_path.write_text(json.dumps({key: "denied"}))
        result = validate_action(action, log_path)
        assert result.executed is False
        assert result.ruling == "denied"
        assert result.rationale is not None


# ---------------------------------------------------------------------------
# Unknown verb
# ---------------------------------------------------------------------------

class TestUnknownVerb:

    def test_unknown_verb_rejected(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        result = validate_action("DELETE everything", log_path)
        assert result.executed is False
        assert result.ruling == "denied"

    def test_malformed_action_rejected(self, tmp_path):
        log_path = tmp_path / "decision_log.json"
        result = validate_action("", log_path)
        assert result.executed is False
