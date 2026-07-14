"""Unit tests for agent runtime helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fade_agent_runtime.agent_loop import gather_context_via_tools
from fade_agent_runtime.diff import parse_unified_diff
from fade_agent_runtime.implementation import parse_implementation_output
from fade_agent_runtime.promotion import PromotionError, promote_workspace_to_source
from fade_domain.goal import Goal, GoalStatus
from fade_domain.ids import GoalId, ProjectId


def test_parse_unified_diff_counts_changes() -> None:
    diff_text = """diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,3 @@
 def greet():
-    return "hi"
+    return "hello"
"""
    files = parse_unified_diff(diff_text)
    assert len(files) == 1
    assert files[0].path == "src/app.py"
    assert files[0].status == "modified"
    assert files[0].additions == 1
    assert files[0].deletions == 1


def test_parse_implementation_output_accepts_fenced_json() -> None:
    raw = """```json
{
  "changes": [{"path": "main.py", "new_content": "print('ok')", "reason": "test"}],
  "summary": "demo"
}
```"""
    parsed = parse_implementation_output(raw)
    assert parsed.summary == "demo"
    assert parsed.changes[0].path == "main.py"


def test_gather_context_via_tools_prefers_intent_matches(tmp_path: Path) -> None:
    src = tmp_path / "src" / "pilot_app"
    src.mkdir(parents=True)
    (src / "main.py").write_text("def greet(): pass\n", encoding="utf-8")
    (src / "ledger.py").write_text("def ledger(): pass\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_main(): pass\n", encoding="utf-8")

    goal = Goal(
        id=GoalId.generate(),
        project_id=ProjectId.generate(),
        title="Ledger",
        intent="Update ledger module",
        constraints=[],
        priority=1,
        status=GoalStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    context = gather_context_via_tools(tmp_path, goal, max_files=3)
    assert "src/pilot_app/ledger.py" in context


def test_promote_workspace_to_source_copies_changed_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    (workspace / "src").mkdir()
    (source / "src").mkdir()
    (workspace / "src" / "main.py").write_text("updated\n", encoding="utf-8")
    (source / "src" / "main.py").write_text("original\n", encoding="utf-8")

    diff_text = """diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -1 +1 @@
-original
+updated
"""
    promoted = promote_workspace_to_source(
        workspace_path=workspace,
        source_path=source,
        diff_text=diff_text,
    )
    assert promoted == ["src/main.py"]
    assert (source / "src" / "main.py").read_text(encoding="utf-8") == "updated\n"


def test_promote_workspace_to_source_rejects_empty_diff(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    try:
        promote_workspace_to_source(
            workspace_path=workspace,
            source_path=source,
            diff_text="",
        )
    except PromotionError as exc:
        assert exc.code == "EMPTY_DIFF"
    else:
        raise AssertionError("expected PromotionError")
