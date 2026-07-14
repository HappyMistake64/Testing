"""Unit tests for project analysis."""

from __future__ import annotations

from pathlib import Path

import pytest
from fade_domain.job import JobState, can_transition, is_terminal
from fade_evidence.ledger import EvidenceLedger
from fade_project_analysis.analyzer import analyze_project
from fade_project_analysis.ignore_engine import IgnoreEngine
from fade_project_analysis.python_parser import parse_python_file
from fade_project_analysis.typescript_parser import parse_typescript_file


class TestIgnoreEngine:
    def test_ignores_node_modules(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        (project / "node_modules").mkdir()
        (project / "node_modules" / "pkg.js").write_text("x", encoding="utf-8")
        (project / "main.py").write_text("def hello(): pass\n", encoding="utf-8")

        engine = IgnoreEngine()
        files = engine.walk_files(project)
        rels = [str(f.relative_to(project)) for f in files]
        assert "main.py" in rels
        assert not any("node_modules" in r for r in rels)


class TestPythonParser:
    def test_extracts_function_and_class(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        source = project / "app.py"
        source.write_text(
            "class Service:\n    pass\n\nasync def run():\n    return 1\n",
            encoding="utf-8",
        )
        result = parse_python_file(source, project)
        assert result is not None
        names = {s.name for s in result.symbols}
        assert "Service" in names
        assert "run" in names


class TestTypeScriptParser:
    def test_extracts_exports(self, tmp_path: Path) -> None:
        project = tmp_path / "proj"
        project.mkdir()
        source = project / "index.ts"
        source.write_text(
            "export function greet() {}\nexport class User {}\nexport interface Profile {}\n",
            encoding="utf-8",
        )
        result = parse_typescript_file(source, project)
        assert result is not None
        names = {s.name for s in result.symbols}
        assert {"greet", "User", "Profile"} <= names


class TestAnalyzer:
    def test_analyze_python_project(self, tmp_path: Path) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
        (project / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")

        result = analyze_project(project)
        assert "python" in result.languages
        assert "pyproject.toml" in result.manifests
        assert any(s.name == "main" for s in result.symbols)


class TestJobStateMachine:
    @pytest.mark.parametrize(
        ("current", "target", "expected"),
        [
            (JobState.QUEUED, JobState.PREPARING, True),
            (JobState.RUNNING, JobState.PAUSED, True),
            (JobState.PAUSED, JobState.RUNNING, True),
            (JobState.COMPLETED, JobState.RUNNING, False),
            (JobState.CANCELLED, JobState.QUEUED, False),
        ],
    )
    def test_transitions(self, current: JobState, target: JobState, expected: bool) -> None:
        assert can_transition(current, target) is expected

    def test_terminal_states(self) -> None:
        assert is_terminal(JobState.COMPLETED)
        assert not is_terminal(JobState.RUNNING)


class TestEvidenceLedger:
    def test_hash_chain_integrity(self) -> None:
        ledger = EvidenceLedger()
        e1 = ledger.append(event_type="JOB_QUEUED", payload={"job": "1"})
        e2 = ledger.append(event_type="JOB_STARTED", payload={"worker": "w1"})
        assert e2.previous_event_hash == e1.event_hash
        assert EvidenceLedger.verify_chain([e1, e2])

    def test_tampered_chain_fails(self) -> None:
        from fade_domain.evidence import EvidenceEvent
        from fade_domain.ids import EvidenceId

        ledger = EvidenceLedger()
        e1 = ledger.append(event_type="A", payload={"x": 1})
        bad = EvidenceEvent(
            id=EvidenceId.generate(),
            sequence=2,
            project_id=None,
            job_id=None,
            actor_type="system",
            actor_id="test",
            event_type="B",
            payload_json='{"x": 2}',
            payload_hash=e1.payload_hash,
            previous_event_hash=e1.event_hash,
            event_hash="deadbeef",
            timestamp=e1.timestamp,
        )
        assert not EvidenceLedger.verify_chain([e1, bad])
