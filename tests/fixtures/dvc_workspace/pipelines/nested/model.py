"""Nested test pipeline model commands."""

import json

from pathlib import Path
from typing import Annotated

import typer


app = typer.Typer()


@app.command()
def find_hyperparameters() -> None:
    """Find hyperparameters."""
    hyperp = {
        "alpha": 42,
        "beta": 7,
    }

    with Path("pipelines/nested/files/hyperparameters.json").open("w") as file:
        json.dump(hyperp, file, indent=4)


@app.command()
def train_model(
    split: Annotated[
        str | None,
        typer.Option("--split"),
    ] = None,
) -> None:
    """Train model."""
    with Path("pipelines/nested/files/dataset.json").open() as file:
        dataset = json.load(file)

    with Path("pipelines/nested/files/hyperparameters.json").open() as file:
        hyperp = json.load(file)

    # this is to check that tred works properly, it should trim out the edge between
    # import-data-blue and train-model
    with Path("pipelines/nested/files/blue.json").open() as file:
        data_blue = json.load(file)

    left = "_".join(list(dataset.keys()))
    right = sum(list(dataset.values())) + hyperp["alpha"] * hyperp["beta"]

    right += data_blue["cyan"]

    model = {left: right}

    directory = Path("pipelines/nested/files/")
    filename = f"model-{split}.json" if split else "model.json"
    filepath = directory / filename

    with filepath.open("w") as file:
        json.dump(model, file, indent=4)


if __name__ == "__main__":
    app()
