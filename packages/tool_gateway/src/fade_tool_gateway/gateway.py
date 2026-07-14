"""Tool Gateway facade for filesystem, git and command tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fade_tool_gateway.policy import PolicyDecision, PolicyCheckResult, ToolPolicy
from fade_tool_gateway.runner import CommandResult, run_command


class ToolGatewayError(Exception):
    """Raised when a tool call is denied or fails."""

    def __init__(self, code: str, message: str, *, policy: PolicyCheckResult | None = None) -> None:
        self.code = code
        self.message = message
        self.policy = policy
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ReadFileResult:
    path: str
    content: str
    size_bytes: int
    redacted: bool


@dataclass(frozen=True, slots=True)
class ListDirEntry:
    name: str
    path: str
    is_dir: bool


@dataclass(frozen=True, slots=True)
class ListDirResult:
    path: str
    entries: list[ListDirEntry]


@dataclass(frozen=True, slots=True)
class GitDiffResult:
    path: str
    diff: str
    exit_code: int


class ToolGateway:
    """Authorized tool execution for agent workflows."""

    def __init__(self, policy: ToolPolicy) -> None:
        self._policy = policy
        self._root = policy._workspace_root  # noqa: SLF001

    def read_file(self, relative_path: str, *, max_bytes: int = 1_000_000) -> ReadFileResult:
        check = self._policy.check_read_path(relative_path)
        self._enforce(check)
        resolved = self._policy._resolve_in_workspace(relative_path)  # noqa: SLF001
        assert resolved is not None
        if not resolved.is_file():
            raise ToolGatewayError("FILE_NOT_FOUND", f"Not a file: {relative_path}")
        raw = resolved.read_bytes()
        if len(raw) > max_bytes:
            raise ToolGatewayError("FILE_TOO_LARGE", f"File exceeds {max_bytes} bytes")
        content = raw.decode("utf-8", errors="replace")
        redacted_content = self._policy.redact_output(content)
        return ReadFileResult(
            path=relative_path,
            content=redacted_content,
            size_bytes=len(raw),
            redacted=redacted_content != content,
        )

    def list_dir(self, relative_path: str = ".") -> ListDirResult:
        check = self._policy.check_read_path(relative_path)
        self._enforce(check)
        resolved = self._policy._resolve_in_workspace(relative_path)  # noqa: SLF001
        assert resolved is not None
        if not resolved.is_dir():
            raise ToolGatewayError("NOT_A_DIRECTORY", f"Not a directory: {relative_path}")
        entries: list[ListDirEntry] = []
        for child in sorted(resolved.iterdir(), key=lambda p: p.name):
            rel = str(child.relative_to(self._root))
            entries.append(
                ListDirEntry(name=child.name, path=rel, is_dir=child.is_dir()),
            )
        return ListDirResult(path=relative_path, entries=entries)

    def safe_run_command(
        self,
        argv: list[str],
        *,
        timeout_s: int = 120,
        network_required: bool = False,
    ) -> CommandResult:
        check = self._policy.check_command(argv, network_required=network_required)
        self._enforce(check)
        result = run_command(
            argv,
            cwd=str(self._root),
            timeout_s=timeout_s,
        )
        return CommandResult(
            argv=result.argv,
            cwd=result.cwd,
            exit_code=result.exit_code,
            stdout=self._policy.redact_output(result.stdout),
            stderr=self._policy.redact_output(result.stderr),
            timed_out=result.timed_out,
        )

    def git_diff(self, *, path: str | None = None, cached: bool = False) -> GitDiffResult:
        argv = ["git", "diff"]
        if cached:
            argv.append("--cached")
        if path:
            argv.append("--")
            argv.append(path)
        check = self._policy.check_command(argv)
        self._enforce(check)
        result = run_command(argv, cwd=str(self._root))
        diff = self._policy.redact_output(result.stdout)
        return GitDiffResult(path=path or ".", diff=diff, exit_code=result.exit_code)

    def _enforce(self, check: PolicyCheckResult) -> None:
        if check.decision == PolicyDecision.DENY:
            raise ToolGatewayError(
                "POLICY_DENIED",
                check.reason,
                policy=check,
            )
        if check.decision == PolicyDecision.REQUIRE_APPROVAL:
            raise ToolGatewayError(
                "POLICY_APPROVAL_REQUIRED",
                check.reason,
                policy=check,
            )

    @classmethod
    def for_workspace(
        cls,
        workspace_path: Path,
        *,
        lease_token: str | None = None,
        expected_lease_token: str | None = None,
        write_allowed: bool = False,
    ) -> ToolGateway:
        policy = ToolPolicy(
            workspace_root=workspace_path,
            lease_token=lease_token,
            expected_lease_token=expected_lease_token,
            write_allowed=write_allowed,
        )
        return cls(policy)
