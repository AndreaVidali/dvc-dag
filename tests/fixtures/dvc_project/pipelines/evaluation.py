"""Fixture commands for model evaluation and reporting."""

from __future__ import annotations

import json

from pathlib import Path
from typing import cast

import typer


JsonScalar = str | int | float
MetricMap = dict[str, JsonScalar]
Record = dict[str, JsonScalar]
RecordMap = dict[str, Record]

DATA_DIR = Path("data")
app = typer.Typer()


def load_metrics(path: Path) -> MetricMap:
    """Load a flat JSON mapping from disk."""
    with path.open() as file:
        return cast("MetricMap", json.load(file))


def load_records(path: Path) -> RecordMap:
    """Load a nested JSON mapping from disk."""
    with path.open() as file:
        return cast("RecordMap", json.load(file))


def write_json(path: Path, payload: object) -> None:
    """Write a JSON object to disk."""
    with path.open("w") as file:
        json.dump(payload, file, indent=4)


@app.command()
def evaluate_model() -> None:
    """Evaluate the baseline model on the feature matrix."""
    baseline_model = load_metrics(DATA_DIR / "baseline_model.json")
    feature_matrix = load_records(DATA_DIR / "feature_matrix.json")

    evaluation_report = {
        "mae_kusd": round(95 / float(baseline_model["score"]), 3),
        "coverage": len(feature_matrix),
    }
    write_json(DATA_DIR / "evaluation_report.json", evaluation_report)


@app.command()
def build_model_card() -> None:
    """Build a compact model card for the baseline model."""
    baseline_model = load_metrics(DATA_DIR / "baseline_model.json")
    evaluation_report = load_metrics(DATA_DIR / "evaluation_report.json")

    model_card = {
        "title": "house-price-demo",
        "model_family": str(baseline_model["model_family"]),
        "mae_kusd": float(evaluation_report["mae_kusd"]),
    }
    write_json(DATA_DIR / "model_card.json", model_card)


if __name__ == "__main__":
    app()
