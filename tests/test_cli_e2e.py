"""End-to-end CLI tests for DVC DAG generation."""

from __future__ import annotations

import importlib.metadata

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from dvc_dag.cli import app
from dvc_dag.draw import draw_dag_image, generate_dag, remove_transitivities


if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from pydot.classes import EdgeEndpoint
    from pydot.core import Dot

    from tests.conftest import DvcProject


runner = CliRunner()


def _clean_name(name: EdgeEndpoint) -> str:
    """Return a graph node or edge endpoint name without Graphviz quotes."""
    return str(name).replace('"', "")


def _node_names(graph: Dot) -> set[str]:
    """Return the normalized set of node names for a pydot graph."""
    return {_clean_name(node.get_name()) for node in graph.get_nodes()}


def _edge_pairs(graph: Dot) -> set[tuple[str, str]]:
    """Return the normalized set of edge endpoints for a pydot graph."""
    return {
        (_clean_name(edge.get_source()), _clean_name(edge.get_destination()))
        for edge in graph.get_edges()
    }


def test_generate_dag_reads_the_fixture_project(
    dvc_project: DvcProject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate the raw DAG from an isolated DVC fixture project."""
    dvc_project.activate(monkeypatch)

    dag = generate_dag()

    assert '"root-train-models@full";' in dag
    assert '"stages/model/dvc.yaml:nested-train-models@out_of_sample";' in dag
    assert '"pipelines/root/data/raw_blue.json.dvc" -> "root-import-data-blue";' in dag
    assert '"root-import-data-blue" -> "root-train-model";' in dag


def test_draw_dag_image_collapses_and_trims_the_fixture_graph(
    dvc_project: DvcProject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trim transitive edges and collapse parametrized stages in the rendered graph."""
    dvc_project.activate(monkeypatch)

    graph = draw_dag_image(
        remove_transitivities(generate_dag()),
        path_text_to_delete=["pipelines/", "stages/"],
        stage_collapses=[
            "root-train-models=split",
            "stages/model/dvc.yaml:nested-train-models=split",
        ],
        colors_random_seed=12,
    )

    node_names = _node_names(graph)
    edge_pairs = _edge_pairs(graph)
    graph_text = graph.to_string()

    assert "root-train-models@{split}" in node_names
    assert "root-train-models@full" not in node_names
    assert "stages/model:\nnested-train-models@{split}" in node_names
    assert "stages/model:\nnested-train-models@out_of_time" not in node_names
    assert ("root-import-data-blue", "root-train-model") not in edge_pairs
    assert (
        "stages/data:\nnested-import-data-blue",
        "stages/model:\nnested-train-model",
    ) not in edge_pairs
    assert "model:<BR/>nested-train-models@{split}" in graph_text
    assert "nested/data:<BR/>raw_blue.json.dvc" in graph_text


def test_cli_writes_a_png_from_the_fixture_project(
    dvc_project: DvcProject,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Run the CLI end to end against the isolated DVC fixture project."""
    dvc_project.activate(monkeypatch)

    output_path = tmp_path / "nested" / "output" / "dag.png"
    result = runner.invoke(
        app,
        [
            "--delete-text",
            "pipelines/",
            "--delete-text",
            "stages/",
            "--collapse-stage",
            "root-train-models=split",
            "--collapse-stage",
            "stages/model/dvc.yaml:nested-train-models=split",
            "--colors-random-seed",
            "12",
            "--out",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert f"DAG saved in {output_path}" in result.stdout


def test_console_script_writes_a_png_from_the_fixture_project(
    dvc_project: DvcProject,
    tmp_path: Path,
) -> None:
    """Run the installed console script against the fixture project."""
    output_path = tmp_path / "console-script" / "dag.png"
    result = dvc_project.run_cli(
        [
            "--delete-text",
            "pipelines/",
            "--delete-text",
            "stages/",
            "--collapse-stage",
            "root-train-models=split",
            "--collapse-stage",
            "stages/model/dvc.yaml:nested-train-models=split",
            "--colors-random-seed",
            "12",
            "--out",
            str(output_path),
        ],
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert f"DAG saved in {output_path}" in result.stdout


def test_cli_rejects_invalid_collapse_stage_values() -> None:
    """Fail fast on invalid collapse-stage values before running DVC commands."""
    result = runner.invoke(
        app,
        [
            "--collapse-stage",
            "invalid-collapse-stage",
        ],
    )

    assert result.exit_code == 2
    assert "Invalid --collapse-stage value" in result.output


def test_console_script_reports_not_in_dvc_repo(
    dvc_project: DvcProject,
    tmp_path: Path,
) -> None:
    """Report a friendly error outside a DVC repository."""
    result = dvc_project.run_cli(
        [],
        cwd=tmp_path,
        env=dvc_project.make_env(),
    )

    assert result.returncode == 1
    assert "Error: Not inside a DVC repository." in result.stderr
    assert "Traceback" not in result.stderr


def test_console_script_reports_missing_dvc(
    dvc_project: DvcProject,
) -> None:
    """Report a friendly error when `dvc` is missing from PATH."""
    result = dvc_project.run_cli(
        [],
        env=dvc_project.make_env(include_dvc=False),
    )

    assert result.returncode == 1
    assert "Error: DVC was not found." in result.stderr
    assert "Traceback" not in result.stderr


def test_console_script_reports_missing_tred(
    dvc_project: DvcProject,
) -> None:
    """Report a friendly error when Graphviz is unavailable."""
    result = dvc_project.run_cli(
        [],
        env=dvc_project.make_env(include_graphviz=False),
    )

    assert result.returncode == 1
    assert "Error: Graphviz `tred` was not found." in result.stderr
    assert "Traceback" not in result.stderr


def test_console_script_debug_keeps_traceback(
    dvc_project: DvcProject,
    tmp_path: Path,
) -> None:
    """Keep traceback-level detail available behind `--debug`."""
    result = dvc_project.run_cli(
        ["--debug"],
        cwd=tmp_path,
        env=dvc_project.make_env(),
    )

    assert result.returncode == 1
    assert "Traceback" in result.stderr
    assert "Not inside a DVC repository" in result.stderr


def test_console_script_supports_version_flag(
    dvc_project: DvcProject,
) -> None:
    """Expose the installed package version from the console script."""
    result = dvc_project.run_cli(["--version"])

    assert result.returncode == 0
    assert result.stdout.strip() == f"dvc-dag {importlib.metadata.version('dvc-dag')}"


def test_module_entrypoint_supports_help(
    dvc_project: DvcProject,
) -> None:
    """Expose the CLI via `python -m dvc_dag`."""
    result = dvc_project.run_module(["--help"])

    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "--version" in result.stdout
