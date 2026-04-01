"""Fixture commands for model training."""

from __future__ import annotations

import json

from pathlib import Path
from typing import Annotated, cast

import typer


JsonScalar = str | int | float
Record = dict[str, JsonScalar]
RecordMap = dict[str, Record]
MetricMap = dict[str, JsonScalar]

DATA_DIR = Path("data")
FAMILY_FACTORS = {
    "linear": 0.97,
    "random_forest": 1.03,
    "gradient_boosting": 1.08,
}
app = typer.Typer()


def load_records(path: Path) -> RecordMap:
    """Load a nested JSON mapping from disk."""
    with path.open() as file:
        return cast("RecordMap", json.load(file))


def load_metrics(path: Path) -> MetricMap:
    """Load a flat JSON mapping from disk."""
    with path.open() as file:
        return cast("MetricMap", json.load(file))


def write_json(path: Path, payload: object) -> None:
    """Write a JSON object to disk."""
    with path.open("w") as file:
        json.dump(payload, file, indent=4)


@app.command()
def search_hyperparameters() -> None:
    """Produce deterministic hyperparameters for the demo model."""
    feature_matrix = load_records(DATA_DIR / "feature_matrix.json")

    average_signal = sum(
        sum(float(value) for value in record.values()) for record in feature_matrix.values()
    ) / len(feature_matrix)
    hyperparameters = {
        "learning_rate": round(0.025 + average_signal / 1000, 3),
        "max_depth": 5,
        "min_samples_leaf": 2,
    }

    write_json(DATA_DIR / "hyperparameters.json", hyperparameters)


def compute_model_score(family: str | None = None) -> float:
    """Return a deterministic model score for the fixture."""
    feature_matrix = load_records(DATA_DIR / "feature_matrix.json")
    hyperparameters = load_metrics(DATA_DIR / "hyperparameters.json")
    market_context = load_records(DATA_DIR / "market_context.json")

    feature_signal = sum(
        float(record["neighborhood_quality"])
        + float(record["market_heat"])
        + float(record["pricing_alignment"])
        for record in feature_matrix.values()
    )
    context_signal = sum(
        float(record["median_price_per_sqft"]) / 100 + float(record["list_price_per_sqft"]) / 100
        for record in market_context.values()
    )
    score = (
        feature_signal
        + context_signal
        + int(hyperparameters["max_depth"]) * 0.9
        - float(hyperparameters["learning_rate"]) * 10
    )

    if family is not None:
        score *= FAMILY_FACTORS[family]

    return round(score, 2)


@app.command()
def train_baseline_model() -> None:
    """Train the baseline house-price model."""
    baseline_model = {
        "model_family": "baseline_regression",
        "score": compute_model_score(),
    }
    write_json(DATA_DIR / "baseline_model.json", baseline_model)


@app.command()
def train_candidate_models(
    family: Annotated[
        str | None,
        typer.Option("--family"),
    ] = None,
) -> None:
    """Train candidate house-price models across model families."""
    if family is None:
        msg = "`--family` is required for candidate-model training."
        raise typer.BadParameter(msg, param_hint="--family")

    candidate_model = {
        "model_family": family,
        "score": compute_model_score(family),
    }
    write_json(DATA_DIR / f"candidate_model-{family}.json", candidate_model)


if __name__ == "__main__":
    app()
