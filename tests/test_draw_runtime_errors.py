"""Unit tests for draw runtime error mapping."""

import re
import subprocess

import pytest

from dvc_dag import draw


def test_draw_dag_image_reports_dot_parse_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrap DOT parser failures with a user-facing error."""

    def broken_parser(_dag: str) -> list[object]:
        msg = "bad dot"
        raise RuntimeError(msg)

    monkeypatch.setattr(draw.pydot, "graph_from_dot_data", broken_parser)

    msg = "Unable to parse the DAG DOT data returned by DVC."
    with pytest.raises(draw.DvcDagError, match=re.escape(msg)):
        draw.draw_dag_image(
            "digraph { broken }",
            path_text_to_delete=[],
            stage_merges=[],
            colors_random_seed=42,
        )


def test_generate_dag_reports_missing_dvc(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report a clear error when DVC is not on PATH."""
    missing_commands = {"dvc": None}

    def fake_which(command: str) -> str | None:
        return missing_commands.get(command)

    monkeypatch.setattr(draw.shutil, "which", fake_which)

    msg = "DVC was not found."
    with pytest.raises(draw.DvcDagError, match=re.escape(msg)):
        draw.generate_dag()


def test_generate_dag_reports_not_in_dvc_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Map DVC's repository error to a friendly message."""
    monkeypatch.setattr(
        draw.shutil,
        "which",
        lambda command: "/usr/bin/dvc" if command == "dvc" else None,
    )

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            1,
            ["/usr/bin/dvc", "dag", "--dot"],
            stderr="ERROR: you are not inside of a DVC repository",
        )

    monkeypatch.setattr(draw.subprocess, "run", fake_run)

    msg = "Not inside a DVC repository."
    with pytest.raises(draw.DvcDagError, match=re.escape(msg)):
        draw.generate_dag()


def test_generate_dag_reports_other_dvc_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preserve DVC stderr for other command failures."""
    monkeypatch.setattr(
        draw.shutil,
        "which",
        lambda command: "/usr/bin/dvc" if command == "dvc" else None,
    )

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            1,
            ["/usr/bin/dvc", "dag", "--dot"],
            stderr="boom",
        )

    monkeypatch.setattr(draw.subprocess, "run", fake_run)

    with pytest.raises(draw.DvcDagError, match="Failed to generate the DVC DAG: boom"):
        draw.generate_dag()


def test_ensure_graphviz_dot_reports_missing_dot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report a clear error when Graphviz dot is not on PATH."""
    missing_commands = {"dot": None}

    def fake_which(command: str) -> str | None:
        return missing_commands.get(command)

    monkeypatch.setattr(draw.shutil, "which", fake_which)

    msg = "Graphviz `dot` was not found."
    with pytest.raises(draw.DvcDagError, match=re.escape(msg)):
        draw.ensure_graphviz_dot()


def test_remove_transitivities_reports_missing_tred(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report a clear error when Graphviz tred is not on PATH."""
    missing_commands = {"tred": None}

    def fake_which(command: str) -> str | None:
        return missing_commands.get(command)

    monkeypatch.setattr(draw.shutil, "which", fake_which)

    msg = "Graphviz `tred` was not found."
    with pytest.raises(draw.DvcDagError, match=re.escape(msg)):
        draw.remove_transitivities("digraph { a -> b }")


def test_remove_transitivities_reports_tred_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrap tred execution failures with a user-facing error."""
    monkeypatch.setattr(
        draw.shutil,
        "which",
        lambda command: "/usr/bin/tred" if command == "tred" else None,
    )

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            1,
            ["/usr/bin/tred"],
            stderr="tred exploded",
        )

    monkeypatch.setattr(draw.subprocess, "run", fake_run)

    with pytest.raises(
        draw.DvcDagError,
        match=r"Graphviz `tred` failed while processing the DVC DAG: tred exploded",
    ):
        draw.remove_transitivities("digraph { a -> b }")
