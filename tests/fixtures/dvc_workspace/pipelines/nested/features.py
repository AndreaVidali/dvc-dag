"""Nested test pipeline feature commands."""

import json

from pathlib import Path

import typer


app = typer.Typer()


@app.command()
def create_dataset() -> None:
    """Create dataset."""
    with Path("pipelines/nested/files/blue.json").open() as file:
        data_blue = json.load(file)

    with Path("pipelines/nested/files/red.json").open() as file:
        data_red = json.load(file)

    dataset = data_blue | data_red

    with Path("pipelines/nested/files/dataset.json").open("w") as file:
        json.dump(dataset, file, indent=4)


if __name__ == "__main__":
    app()
