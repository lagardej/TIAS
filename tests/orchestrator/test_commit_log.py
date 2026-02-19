"""
tests/orchestrator/test_commit_log.py

Unit tests for src/orchestrator/commit_log.py.
Uses tmp_path for log file isolation.
"""

import pytest
from pathlib import Path

from src.orchestrator.parse_response import ParsedResponse
from src.orchestrator.validate_action import ActionResult
from src.orchestrator.commit_log import CommitContext, commit_log, make_session_id
from src.orchestrator.llm_call import _FALLBACK_RESPONSE


def _ctx(**kwargs) -> CommitContext:
    defaults = dict(
        session_id="2026-02-19_143201",
        flow_type="standard",
        tier=1,
        speaker="Wale Oluwaseun",
        query="Should we proceed?",
        parsed=ParsedResponse(
            thought="domain check",
            action="FETCH something",
            chat="Wale: Na so e be.",
            action_valid=True,
            fallback_used=False,
        ),
        action_result=ActionResult(executed=True, ruling="fetch"),
    )
    defaults.update(kwargs)
    return CommitContext(**defaults)


# ---------------------------------------------------------------------------
# Log file creation
# ---------------------------------------------------------------------------

class TestLogFile:

    def test_creates_log_file_on_first_turn(self, tmp_path):
        commit_log(_ctx(), logs_dir=tmp_path)
        log_file = tmp_path / "session_2026-02-19_143201.log"
        assert log_file.exists()

    def test_appends_on_subsequent_turns(self, tmp_path):
        commit_log(_ctx(), logs_dir=tmp_path)
        commit_log(_ctx(), logs_dir=tmp_path)
        log_file = tmp_path / "session_2026-02-19_143201.log"
        content = log_file.read_text()
        assert content.count("=== TURN END ===") == 2

    def test_creates_logs_dir_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "logs"
        commit_log(_ctx(), logs_dir=nested)
        assert nested.exists()


# ---------------------------------------------------------------------------
# Log content
# ---------------------------------------------------------------------------

class TestLogContent:

    def _read(self, tmp_path) -> str:
        commit_log(_ctx(), logs_dir=tmp_path)
        return (tmp_path / "session_2026-02-19_143201.log").read_text()

    def test_query_in_log(self, tmp_path):
        assert "Should we proceed?" in self._read(tmp_path)

    def test_chat_in_log(self, tmp_path):
        assert "Wale: Na so e be." in self._read(tmp_path)

    def test_thought_in_log(self, tmp_path):
        assert "[THOUGHT]" in self._read(tmp_path)

    def test_action_status_in_log(self, tmp_path):
        assert "[OK]" in self._read(tmp_path)

    def test_rejected_action_shown(self, tmp_path):
        ctx = _ctx(action_result=ActionResult(executed=False, ruling="denied", rationale="forbidden"))
        commit_log(ctx, logs_dir=tmp_path)
        content = (tmp_path / "session_2026-02-19_143201.log").read_text()
        assert "[REJECTED]" in content

    def test_session_header_present(self, tmp_path):
        content = self._read(tmp_path)
        assert "=== SESSION 2026-02-19_143201 | TIER 1 | STANDARD ===" in content


# ---------------------------------------------------------------------------
# Log write failure
# ---------------------------------------------------------------------------

class TestLogWriteFailure:

    def test_raises_on_log_write_failure(self, tmp_path):
        # Make logs_dir a file to force OSError
        bad_path = tmp_path / "not_a_dir"
        bad_path.write_text("block")
        with pytest.raises(OSError):
            commit_log(_ctx(), logs_dir=bad_path)


# ---------------------------------------------------------------------------
# session_id helper
# ---------------------------------------------------------------------------

class TestMakeSessionId:

    def test_returns_string(self):
        assert isinstance(make_session_id(), str)

    def test_format(self):
        sid = make_session_id()
        assert sid[10] == "_"
        # Validate format rather than fixed length (hour zero-padded but let's be safe)
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}_\d{6}", sid), f"Unexpected format: {sid}"
