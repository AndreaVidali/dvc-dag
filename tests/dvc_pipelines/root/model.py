import json

from pathlib import Path

import click


@click.group(name="cli")
def cli() -> None:
    """Model main entry point."""


@cli.command(name="find-hyperparameters")
def find_hyperparameters() -> None:
    """Find hyperparameters."""
    hyperp = {
        "alpha": 42,
        "beta": 7,
    }

    with Path("tests/dvc_pipelines/root/files/hyperparameters.json").open("w") as file:
        json.dump(hyperp, file, indent=4)


@cli.command(name="train-model")
@click.option("--kind", type=click.STRING)
def train_model(kind: str | None) -> None:
    """Train model."""
    with Path("tests/dvc_pipelines/root/files/dataset.json").open() as file:
        dataset = json.load(file)

    with Path("tests/dvc_pipelines/root/files/hyperparameters.json").open() as file:
        hyperp = json.load(file)

    # this is to check that tred works properly, it should trim out the edge between
    # import-data-blue and train-model
    with Path("tests/dvc_pipelines/root/files/blue.json").open() as file:
        data_blue = json.load(file)

    left = "_".join(list(dataset.keys()))
    right = sum(list(dataset.values())) + hyperp["alpha"] * hyperp["beta"]

    right += data_blue["cyan"]

    model = {left: right}

    directory = Path("tests/dvc_pipelines/root/files/")
    filename = f"model-{kind}.json" if kind else "model.json"
    filepath = directory / filename

    with filepath.open("w") as file:
        json.dump(model, file, indent=4)


if __name__ == "__main__":
    cli()
