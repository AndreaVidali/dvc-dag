"""CLI main entry point."""

import logging

from pathlib import Path
from typing import Annotated

import typer

from dvc_dag.draw import draw_dag_image, generate_dag, parse_stage_merges, remove_transitivies
from dvc_dag.logger import configure_logging, logger


app = typer.Typer()


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
    merge_stage: Annotated[
        list[str] | None,
        typer.Option(
            "--merge-stage",
            help=(
                "Delete the parametrization part of a parametrize stage by collapsing all "
                "stages into one. Can be specified multiple times. "
                "Format: 'stage_name|replacement' or "
                "'path/to/dvc.yaml:stage_name|replacement'"
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
        dvc-dag --delete-text "dvc_pipelines/" --delete-text "tests/" \\
            --merge-stage "train-models|kind" \\
            --merge-stage "dvc_pipelines/model/dvc.yaml:train-models|kind"
    """
    configure_logging(level=logging.DEBUG if debug else logging.INFO)

    delete_text_values = delete_text or []
    merge_stage_values = merge_stage or []
    out = out.expanduser()

    try:
        parse_stage_merges(merge_stage_values)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--merge-stage") from exc

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        msg = f"Cannot create the parent directory for {out!s}: {exc}"
        raise typer.BadParameter(msg, param_hint="--out") from exc

    if debug:
        logger.debug("Debug mode enabled.")

    dag = generate_dag()
    logger.debug(f"Raw dag: {dag}")

    dag_tred = remove_transitivies(dag)
    logger.debug(f"Trimmed dag: {dag_tred}")

    dag_image = draw_dag_image(
        dag_tred,
        path_text_to_delete=delete_text_values,
        stage_merges=merge_stage_values,
        colors_random_seed=colors_random_seed,
    )
    try:
        write_succeeded = dag_image.write(str(out), format="png")
    except OSError as exc:
        msg = f"Cannot write the PNG to {out!s}: {exc}"
        raise typer.BadParameter(msg, param_hint="--out") from exc

    if not write_succeeded:
        msg = f"Failed to write the PNG to {out!s}."
        raise typer.BadParameter(msg, param_hint="--out")

    typer.echo(f"DAG saved in {out}")


if __name__ == "__main__":
    app()
