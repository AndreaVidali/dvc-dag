"""Tests for committed docs assets."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DAG = REPO_ROOT / "tests" / "fixtures" / "dvc_project" / "docs" / "dvc_project_dag.png"
DOCS_DAG = REPO_ROOT / "docs" / "dvc_project_dag.png"


def test_docs_demo_dag_matches_the_fixture_dag() -> None:
    """Keep the README demo image synchronized with the fixture output."""
    assert FIXTURE_DAG.exists()
    assert DOCS_DAG.exists()
    assert DOCS_DAG.read_bytes() == FIXTURE_DAG.read_bytes()
