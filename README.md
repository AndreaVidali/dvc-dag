# DVC dag

Generate a clear diagram of your DVC pipeline.

## Overview

DVC provides a built-in DAG visualization using `dvc dag`, but in projects with multiple interconnected stages, it quickly becomes cluttered and hard to read.

This tool enhances `dvc dag` by generating a **PNG image** of the DAG with improved readability. It applies various optimizations, including:

- **Trimming unnecessary edges** for a cleaner look.
- **Compressing parameterized stages** to reduce clutter.
- **Simplifying stage names** for better clarity.
- **Using colors and shapes** to distinguish different types of nodes.

## Requirements

This tool requires **Graphviz** to process and render the DAG (installed via brew).

🔗 [Download and install Graphviz](https://graphviz.org/download/) before using this tool.

## Usage

Generate the DAG image by running:

```bash
dvc-dag
```

For additional customization options, run:

```bash
dvc-dag --help
```

## Development

This repository includes dummy DVC pipelines used solely for testing purposes.
