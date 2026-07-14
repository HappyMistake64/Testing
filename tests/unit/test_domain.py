"""Domain unit tests."""

from __future__ import annotations

import pytest
from fade_domain.ids import JobId, ProjectId
from fade_domain.types import AutonomyLevel, ErrorCode, RiskLevel


class TestProjectId:
    def test_generate_valid_id(self) -> None:
        pid = ProjectId.generate()
        assert len(pid) == 26
        assert ProjectId.from_string(str(pid)) == pid

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ProjectId"):
            ProjectId("not-a-valid-ulid")


class TestJobId:
    def test_generate_valid_id(self) -> None:
        jid = JobId.generate()
        assert len(jid) == 26


class TestRiskLevel:
    def test_from_string_valid(self) -> None:
        assert RiskLevel.from_string("HIGH") == RiskLevel.HIGH

    def test_from_string_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid RiskLevel"):
            RiskLevel.from_string("extreme")


class TestAutonomyLevel:
    def test_from_string_valid(self) -> None:
        assert AutonomyLevel.from_string("plan") == AutonomyLevel.PLAN

    def test_from_string_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid AutonomyLevel"):
            AutonomyLevel.from_string("unlimited")


class TestErrorCode:
    def test_error_codes_are_stable(self) -> None:
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
