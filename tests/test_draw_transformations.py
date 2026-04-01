"""Unit tests for draw and color helpers."""

import random

import pydot
import pytest

from dvc_dag.colors import Colors
from dvc_dag.draw import (
    encode_edge_name,
    format_displayed_name,
    format_edges,
    format_nodes,
    parse_stage_collapses,
    process_node_name,
)


def graph_from_dot(dot_data: str) -> pydot.Dot:
    """Return the first graph parsed from DOT data."""
    graphs = pydot.graph_from_dot_data(dot_data)
    assert graphs is not None
    assert len(graphs) == 1
    return graphs[0]


def test_colors_does_not_change_global_random_state() -> None:
    """Constructing Colors should not reseed the module-level RNG."""
    expected_rng = random.Random(123)  # noqa: S311
    expected_value = expected_rng.random()

    random.seed(123)
    _ = Colors(random_seed=42)

    assert random.random() == expected_value  # noqa: S311


def test_colors_are_deterministic_for_a_seed() -> None:
    """Equal seeds should assign the same category colors."""
    colors_a = Colors(random_seed=7)
    colors_b = Colors(random_seed=7)

    root_color_a = colors_a.get_category_color("root")
    nested_color_a = colors_a.get_category_color("nested")
    root_color_b = colors_b.get_category_color("root")
    nested_color_b = colors_b.get_category_color("nested")

    assert root_color_a == root_color_b
    assert nested_color_a == nested_color_b
    assert colors_a.get_category_color("root") == root_color_a
    assert root_color_a != nested_color_a


def test_process_node_name_supports_windows_style_paths() -> None:
    """Normalize Windows-like paths before formatting graph node names."""
    stage_collapses = parse_stage_collapses(
        [r"stages\model\dvc.yaml:train-candidate-models=family"],
    )

    assert (
        process_node_name(
            r"stages\model\dvc.yaml:train-candidate-models@linear",
            stage_collapses=stage_collapses,
        )
        == '"stages/model:\ntrain-candidate-models@{family}"'
    )
    assert (
        process_node_name(
            r"data\listings_raw.json.dvc",
            stage_collapses=stage_collapses,
        )
        == '"data:\nlistings_raw.json.dvc"'
    )


def test_format_displayed_name_collapses_deleted_root_path() -> None:
    """Display only the stage name when the path prefix is fully removed."""
    assert (
        format_displayed_name(
            '"tests:\ntrain-models"',
            path_text_to_delete=["tests"],
            fillcolor="black",
        )
        == "<<FONT COLOR='white'>train-models</FONT>>"
    )


def test_format_nodes_formats_files_and_collapsed_stage_labels() -> None:
    """Apply file path shortening and stage relabeling consistently."""
    graph = graph_from_dot(
        """
        digraph {
            "stages/model/dvc.yaml:train-candidate-models@linear"
                -> "data/listings_raw.json.dvc";
        }
        """,
    )
    stage_collapses = parse_stage_collapses(
        ["stages/model/dvc.yaml:train-candidate-models=family"],
    )

    formatted_nodes = format_nodes(
        graph,
        path_text_to_delete=[],
        stage_collapses=stage_collapses,
        colors_random_seed=11,
    )

    collapsed_stage = '"stages/model:\ntrain-candidate-models@{family}"'
    data_file = '"data:\nlistings_raw.json.dvc"'
    collapsed_stage_label = formatted_nodes[collapsed_stage]["label"]
    data_file_label = formatted_nodes[data_file]["label"]

    assert formatted_nodes[collapsed_stage]["style"] == "filled"
    assert isinstance(collapsed_stage_label, str)
    assert "<BR/>train-candidate-models@{family}</FONT>>" in collapsed_stage_label
    assert formatted_nodes[data_file]["shape"] == "box"
    assert data_file_label == "<<FONT COLOR='black'>data:<BR/>listings_raw.json.dvc</FONT>>"


def test_format_edges_relabels_collapsed_stage_endpoints() -> None:
    """Relabel stage endpoints before encoding edge names."""
    graph = graph_from_dot(
        """
        digraph {
            "build-analytics-base"
                -> "stages/model/dvc.yaml:train-candidate-models@linear";
        }
        """,
    )
    stage_collapses = parse_stage_collapses(
        [
            "stages/model/dvc.yaml:train-candidate-models=family",
        ],
    )

    formatted_edges = format_edges(graph, stage_collapses=stage_collapses)

    assert formatted_edges == {
        encode_edge_name(
            '"build-analytics-base"',
            '"stages/model:\ntrain-candidate-models@{family}"',
        ): {"penwidth": "2"},
    }


@pytest.mark.parametrize(
    "stage_collapse",
    [
        "missing-separator",
        "=parameter",
        "stage=",
        "stage=parameter=extra",
    ],
)
def test_parse_stage_collapses_rejects_invalid_values(stage_collapse: str) -> None:
    """Reject malformed collapse-stage values."""
    with pytest.raises(ValueError, match=r"Invalid --collapse-stage value"):
        parse_stage_collapses([stage_collapse])


def test_parse_stage_collapses_rejects_conflicting_values() -> None:
    """Reject conflicting parameter names for the same stage."""
    with pytest.raises(ValueError, match=r"Conflicting --collapse-stage values"):
        parse_stage_collapses(["train-candidate-models=family", "train-candidate-models=horizon"])
