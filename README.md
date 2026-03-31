# dvc-dag

Generate a readable PNG diagram of your DVC pipeline.

![Example DVC DAG](https://raw.githubusercontent.com/AndreaVidali/dvc-dag/main/docs/dvc_dag.png)

## Overview

The bundled `dvc dag` command is useful, but larger pipelines quickly become hard to read.

`dvc-dag` renders the pipeline as a PNG and applies a few readability
improvements:

- trims transitive edges
- collapses parameterized stages when requested
- simplifies displayed paths
- uses colors and shapes to distinguish nodes

## Requirements

`dvc-dag` supports Python 3.10 and newer.

`dvc-dag` must be run inside a Git repository initialized with DVC.

It also requires Graphviz on your `PATH`, specifically the `dot` and `tred`
executables.

Install Graphviz with your system package manager:

- macOS: `brew install graphviz`
- Debian/Ubuntu: `sudo apt-get install graphviz`
- Windows: install Graphviz from <https://graphviz.org/download/>

## Installation

Install the package from PyPI:

```bash
pip install dvc-dag
```

Or install it as an isolated CLI:

```bash
pipx install dvc-dag
```

## Usage

Generate a PNG in the current DVC repository:

```bash
dvc-dag --out docs/dvc_dag.png
```

Show all options:

```bash
dvc-dag --help
```

Show the installed version:

```bash
dvc-dag --version
```

Collapse parameterized stages:

```bash
dvc-dag --merge-stage "train-models|kind"
```

The `--merge-stage` format is:

```text
stage_name|replacement
path/to/dvc.yaml:stage_name|replacement
```

## Troubleshooting

- `DVC was not found`: install `dvc` and ensure it is on your `PATH`.
- `Not inside a DVC repository`: run `dvc init` in the project first.
- `Graphviz dot/tred was not found`: install Graphviz and ensure both tools are on your `PATH`.

## Development

The repository includes committed DVC fixture workspaces under `tests/fixtures/`
for end-to-end testing.

You can try the CLI manually against the committed fixture workspace:

```bash
cd tests/fixtures/dvc_workspace
uv run dvc-dag --out /tmp/dvc_dag.png
```

Or render the fixture DAG straight from the repository root:

```bash
make dag
```
