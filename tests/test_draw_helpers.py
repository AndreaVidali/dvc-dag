"""Unit tests for draw and color helpers."""

import random

import pytest

from dvc_dag.colors import Colors
from dvc_dag.draw import parse_stage_merges, process_node_name


def test_colors_does_not_change_global_random_state() -> None:
    """Constructing Colors should not reseed the module-level RNG."""
    expected_rng = random.Random(123)  # noqa: S311
    expected_value = expected_rng.random()

    random.seed(123)
    _ = Colors(random_seed=42)

    assert random.random() == expected_value  # noqa: S311


def test_process_node_name_supports_windows_style_paths() -> None:
    """Normalize Windows-like paths before formatting graph node names."""
    stage_merges = parse_stage_merges(
        [r"dvc_pipelines\model\dvc.yaml:nested-train-models|kind"],
    )

    assert (
        process_node_name(
            r"dvc_pipelines\model\dvc.yaml:nested-train-models@full",
            stage_merges=stage_merges,
        )
        == '"dvc_pipelines/model:\nnested-train-models@kind"'
    )
    assert (
        process_node_name(
            r"tests\dvc_pipelines\root\files\raw_blue.json.dvc",
            stage_merges=stage_merges,
        )
        == '"tests/dvc_pipelines/root/files:\nraw_blue.json.dvc"'
    )


@pytest.mark.parametrize(
    "stage_merge",
    [
        "missing-separator",
        "|replacement",
        "stage|",
        "stage|replacement|extra",
    ],
)
def test_parse_stage_merges_rejects_invalid_values(stage_merge: str) -> None:
    """Reject malformed merge-stage values."""
    with pytest.raises(ValueError, match=r"Invalid --merge-stage value"):
        parse_stage_merges([stage_merge])


def test_parse_stage_merges_rejects_conflicting_values() -> None:
    """Reject conflicting replacements for the same stage."""
    with pytest.raises(ValueError, match=r"Conflicting --merge-stage values"):
        parse_stage_merges(["train-models|kind", "train-models|variant"])
