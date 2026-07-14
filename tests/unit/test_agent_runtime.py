"""Unit tests for agent runtime helpers."""

from __future__ import annotations

from fade_agent_runtime.diff import parse_unified_diff
from fade_agent_runtime.implementation import parse_implementation_output


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
