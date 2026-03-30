import json

from pathlib import Path

import click


@click.group(name="cli")
def cli() -> None:
    """Features main entry point."""


@cli.command(name="create-dataset")
def create_dataset() -> None:
    """Create dataset."""
    with Path("tests/dvc_pipelines/root/files/blue.json").open() as file:
        data_blue = json.load(file)

    with Path("tests/dvc_pipelines/root/files/red.json").open() as file:
        data_red = json.load(file)

    dataset = data_blue | data_red

    with Path("tests/dvc_pipelines/root/files/dataset.json").open("w") as file:
        json.dump(dataset, file, indent=4)


if __name__ == "__main__":
    cli()
