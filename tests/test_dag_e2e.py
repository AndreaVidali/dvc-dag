"""End-to-end tests for DVC DAG generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from dvc_dag.cli import app
from dvc_dag.draw import draw_dag_image, generate_dag, remove_transitivies


if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from pydot.classes import EdgeEndpoint
    from pydot.core import Dot

    from tests.conftest import DvcWorkspace


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


def test_generate_dag_reads_the_fixture_workspace(
    e2e_workspace: DvcWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate the raw DAG from an isolated DVC fixture workspace."""
    e2e_workspace.activate(monkeypatch)

    dag = generate_dag()

    assert '"root-train-models@full";' in dag
    assert '"dvc_pipelines/model/dvc.yaml:nested-train-models@out_of_sample";' in dag
    assert '"tests/dvc_pipelines/root/files/raw_blue.json.dvc" -> "root-import-data-blue";' in dag
    assert '"root-import-data-blue" -> "root-train-model";' in dag


def test_draw_dag_image_merges_and_trims_the_fixture_graph(
    e2e_workspace: DvcWorkspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trim transitive edges and merge parametrized stages in the rendered graph."""
    e2e_workspace.activate(monkeypatch)

    graph = draw_dag_image(
        remove_transitivies(generate_dag()),
        path_text_to_delete=["dvc_pipelines/", "tests/"],
        stages_merge=[
            "root-train-models|kind",
            "dvc_pipelines/model/dvc.yaml:nested-train-models|kind",
        ],
        colors_random_seed=12,
    )

    node_names = _node_names(graph)
    edge_pairs = _edge_pairs(graph)
    graph_text = graph.to_string()

    assert "root-train-models@kind" in node_names
    assert "root-train-models@full" not in node_names
    assert "dvc_pipelines/model:\nnested-train-models@kind" in node_names
    assert "dvc_pipelines/model:\nnested-train-models@out_of_time" not in node_names
    assert ("root-import-data-blue", "root-train-model") not in edge_pairs
    assert (
        "dvc_pipelines/data:\nnested-import-data-blue",
        "dvc_pipelines/model:\nnested-train-model",
    ) not in edge_pairs
    assert "features:<BR/>nested-create-dataset" in graph_text
    assert "nested/files:<BR/>raw_blue.json.dvc" in graph_text


def test_cli_writes_a_png_from_the_fixture_workspace(
    e2e_workspace: DvcWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Run the CLI end to end against the isolated DVC fixture workspace."""
    e2e_workspace.activate(monkeypatch)

    output_path = tmp_path / "dag.png"
    result = runner.invoke(
        app,
        [
            "--delete-text",
            "dvc_pipelines/",
            "--delete-text",
            "tests/",
            "--merge-stage",
            "root-train-models|kind",
            "--merge-stage",
            "dvc_pipelines/model/dvc.yaml:nested-train-models|kind",
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
