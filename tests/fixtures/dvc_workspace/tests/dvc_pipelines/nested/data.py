"""Nested test pipeline data commands."""

import json

from pathlib import Path

import typer


app = typer.Typer()


def import_data(color: str) -> None:
    """Import data."""
    with Path(f"tests/dvc_pipelines/nested/files/raw_{color}.json").open() as file:
        data = json.load(file)

    imported_data = {key.replace("raw_", ""): value for key, value in data.items()}

    with Path(f"tests/dvc_pipelines/nested/files/{color}.json").open("w") as file:
        json.dump(imported_data, file, indent=4)


@app.command()
def import_data_blue() -> None:
    """Import data blue."""
    import_data("blue")


@app.command()
def import_data_red() -> None:
    """Import data red."""
    import_data("red")


@app.command()
def do_unrelated_stuff() -> None:
    """Do unrelated stuff."""
    with Path("tests/dvc_pipelines/nested/files/unrelated.json").open("w") as file:
        json.dump({"unrelated": "stuff"}, file, indent=4)


if __name__ == "__main__":
    app()
