"""CLI main entry point."""

import logging

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

import typer

from dvc_dag.draw import (
    DvcDagError,
    draw_dag_image,
    ensure_graphviz_dot,
    generate_dag,
    parse_stage_collapses,
    remove_transitivities,
)
from dvc_dag.logger import configure_logging, logger


app = typer.Typer()


def _resolve_package_version() -> str:
    """Return the installed package version."""
    try:
        return version("dvc-dag")
    except PackageNotFoundError:
        return "0+unknown"


def _version_callback(value: bool) -> None:  # noqa: FBT001
    """Print the package version and exit."""
    if value:
        typer.echo(f"dvc-dag {_resolve_package_version()}")
        raise typer.Exit


def _abort_runtime_error(message: str) -> None:
    """Print a friendly runtime error and exit."""
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@app.command()
def main(
    *,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Debug mode.",
            show_default=True,
        ),
    ] = False,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            expose_value=False,
            help="Show the package version and exit.",
            is_eager=True,
        ),
    ] = None,
    out: Annotated[
        Path,
        typer.Option(
            "--out",
            help="The file where the PNG dag is saved.",
            show_default=True,
            exists=False,
            file_okay=True,
            dir_okay=False,
            writable=True,
            resolve_path=False,
        ),
    ] = Path("dvc_dag.png"),
    delete_text: Annotated[
        list[str] | None,
        typer.Option(
            "--delete-text",
            help=(
                "The string of text to remove in the 'path' section of each stage name. "
                "Can be specified multiple times."
            ),
        ),
    ] = None,
    collapse_stage: Annotated[
        list[str] | None,
        typer.Option(
            "--collapse-stage",
            help=(
                "Collapse a parametrized stage by replacing concrete values with the chosen "
                "parameter name. Can be specified multiple times. "
                "Format: 'stage_name=parameter_name' or "
                "'path/to/dvc.yaml:stage_name=parameter_name'"
            ),
        ),
    ] = None,
    colors_random_seed: Annotated[
        int,
        typer.Option(
            "--colors-random-seed",
            help="Set the random seed for the colors assigned to each node.",
            show_default=True,
        ),
    ] = 42,
) -> None:
    r"""Draw the DVC dag as PNG.

    Example:
        dvc-dag --delete-text "pipelines/" --delete-text "stages/" \\
            --collapse-stage "train-candidate-models=family" \\
            --collapse-stage "stages/model/dvc.yaml:train-candidate-models=family"
    """
    configure_logging(level=logging.DEBUG if debug else logging.INFO)

    delete_text_values = delete_text or []
    collapse_stage_values = collapse_stage or []
    out = out.expanduser()

    try:
        parse_stage_collapses(collapse_stage_values)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--collapse-stage") from exc

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        msg = f"Cannot create the parent directory for {out!s}: {exc}"
        raise typer.BadParameter(msg, param_hint="--out") from exc

    if debug:
        logger.debug("Debug mode enabled.")

    try:
        dag = generate_dag()
        logger.debug(f"Raw dag: {dag}")

        dag_tred = remove_transitivities(dag)
        logger.debug(f"Trimmed dag: {dag_tred}")

        dag_image = draw_dag_image(
            dag_tred,
            path_text_to_delete=delete_text_values,
            stage_collapses=collapse_stage_values,
            colors_random_seed=colors_random_seed,
        )
    except DvcDagError as exc:
        if debug:
            raise
        _abort_runtime_error(str(exc))

    try:
        ensure_graphviz_dot()
        write_succeeded = dag_image.write(str(out), format="png")
    except OSError as exc:
        msg = f"Cannot write the PNG to {out!s}: {exc}"
        raise typer.BadParameter(msg, param_hint="--out") from exc
    except Exception as exc:
        if debug:
            raise
        _abort_runtime_error(f"Failed to write the PNG to {out!s}: {exc}")

    if not write_succeeded:
        _abort_runtime_error(f"Failed to write the PNG to {out!s}.")

    typer.echo(f"DAG saved in {out}")


if __name__ == "__main__":
    app()
