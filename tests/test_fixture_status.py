"""Integrity checks for the committed DVC fixture project."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from tests.conftest import DvcProject


def test_publish_project_dag_is_up_to_date(committed_dvc_project: DvcProject) -> None:
    """Keep the committed fixture DAG stage in a clean, non-mutating state."""
    result = committed_dvc_project.run_dvc(["status", "publish-project-dag"])

    assert result.returncode == 0, result.stderr
    assert "Data and pipelines are up to date." in result.stdout
