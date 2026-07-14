"""Tool Gateway policy enforcement tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fade_tool_gateway.gateway import ToolGateway, ToolGatewayError
from fade_tool_gateway.policy import ToolPolicy


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=sk-abcdefghijklmnopqrstuvwxyz123456\n", encoding="utf-8")
    (root / "subdir").mkdir()
    (root / "subdir" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    return root


class TestToolGatewayPolicy:
    def test_read_file_in_workspace(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        result = gw.read_file("README.md")
        assert "hello" in result.content

    def test_deny_protected_env_file(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        with pytest.raises(ToolGatewayError) as exc:
            gw.read_file(".env")
        assert exc.value.code == "POLICY_DENIED"

    def test_deny_path_traversal(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        with pytest.raises(ToolGatewayError) as exc:
            gw.read_file("../../etc/passwd")
        assert exc.value.code == "POLICY_DENIED"

    def test_list_dir(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        result = gw.list_dir(".")
        names = {e.name for e in result.entries}
        assert "README.md" in names
        assert "subdir" in names

    def test_deny_unknown_command(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        with pytest.raises(ToolGatewayError) as exc:
            gw.safe_run_command(["rm", "-rf", "/"])
        assert exc.value.code in {"POLICY_DENIED", "POLICY_APPROVAL_REQUIRED"}

    def test_allow_python_check(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        result = gw.safe_run_command(["python", "-c", "print('ok')"])
        assert result.exit_code == 0
        assert "ok" in result.stdout

    def test_write_requires_lease(self, workspace: Path) -> None:
        policy = ToolPolicy(workspace_root=workspace, write_allowed=False)
        check = policy.check_write_path("new_file.py")
        assert check.decision.value == "deny"

    def test_write_with_valid_lease(self, workspace: Path) -> None:
        policy = ToolPolicy(
            workspace_root=workspace,
            write_allowed=True,
            lease_token="token-a",
            expected_lease_token="token-a",
        )
        check = policy.check_write_path("new_file.py")
        assert check.decision.value == "allow"

    def test_write_denied_with_invalid_lease(self, workspace: Path) -> None:
        policy = ToolPolicy(
            workspace_root=workspace,
            write_allowed=True,
            lease_token="token-a",
            expected_lease_token="token-b",
        )
        check = policy.check_write_path("new_file.py")
        assert check.decision.value == "deny"

    def test_git_diff_allowed(self, workspace: Path) -> None:
        gw = ToolGateway.for_workspace(workspace)
        # Non-git workspace: git diff may fail but policy should allow attempt
        try:
            result = gw.git_diff()
            assert isinstance(result.exit_code, int)
        except ToolGatewayError as exc:
            assert exc.code != "POLICY_DENIED"
