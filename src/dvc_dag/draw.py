"""Graph transformation and rendering helpers for DVC DAG output."""

from __future__ import annotations

import shutil
import subprocess

from copy import deepcopy
from typing import TYPE_CHECKING

import pydot

from pydot.core import Dot, Edge, Node

from dvc_dag.colors import Colors, needs_white_text
from dvc_dag.logger import logger


if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydot.classes import EdgeEndpoint


ROOT_CATEGORY = "root"
EDGE_NAME_SEPARATOR = "***"
DEFAULT_NODE_OPTIONS: dict[str, str | int] = {
    "fontsize": 20,
    "penwidth": "2",
    "fontname": "Cambria",
}
DEFAULT_EDGE_OPTIONS: dict[str, str] = {
    "penwidth": "2",
}


def normalize_endpoint(endpoint: EdgeEndpoint) -> str:
    """Return a string endpoint from pydot edge data."""
    if isinstance(endpoint, str):
        return endpoint

    msg = f"Unsupported edge endpoint type: {type(endpoint).__name__}"
    raise TypeError(msg)


def get_all_nodes(graph: Dot) -> list[str]:
    """Return the list of nodes in the graph."""
    edges = graph.get_edge_list()

    connected_nodes = [
        normalize_endpoint(endpoint)
        for edge in edges
        for endpoint in (edge.get_source(), edge.get_destination())
    ]
    connected_nodes = list(dict.fromkeys(connected_nodes))

    unconnected_nodes = [node.get_name() for node in graph.get_nodes()]
    unconnected_nodes = [node for node in unconnected_nodes if not node.endswith('.dvc"')]

    return unconnected_nodes + connected_nodes


def process_node_name(name: str, stages_merge: Sequence[str]) -> str:
    """Process the name of the node."""
    name = name.replace('"', "")

    is_dvc_parametrization = "@" in name
    if is_dvc_parametrization:
        # is a stage with parametrization
        stage_name, parametrization = name.split("@")

        for stage_merge in stages_merge:
            real_name, simpler_name = stage_merge.split("|")
            if stage_name == real_name:
                name = name.replace(parametrization, simpler_name)

    is_nested_dvc_stage = ":" in name
    is_file = "/" in name and not is_nested_dvc_stage

    if is_nested_dvc_stage:
        # is a nested dvc stage
        dvc_file, stage = name.split(":")
        group = dvc_file.replace("/dvc.yaml", "")
        new_name = f"{group}:\n{stage}"

    elif is_file:
        # is a file
        name_splitted = name.split("/")
        filepath = "/".join(name_splitted[:-1])
        filename = name_splitted[-1]
        new_name = f"{filepath}:\n{filename}"

    else:
        # is a root dvc stage
        new_name = name

    return f'"{new_name}"'


def encode_edge_name(source: str, dest: str) -> str:
    """Encode the edge name."""
    return source + EDGE_NAME_SEPARATOR + dest


def decode_edge_name(name: str) -> tuple[str, str]:
    """Decode the edge name."""
    source, dest = name.split(EDGE_NAME_SEPARATOR, maxsplit=1)
    return source, dest


def escape_newlines(txt: str) -> str:
    """Return a string with escaped newlines."""
    return txt.replace("\n", "\\n")


def format_displayed_name(
    name: str,
    path_text_to_delete: Sequence[str],
    fillcolor: str | None = None,
) -> str:
    """Format the name shown in the node.

    For the possible attributes: https://www.graphviz.org/doc/info/shapes.html
    """
    text_color = "white" if fillcolor and needs_white_text(fillcolor) else "black"

    name = name.replace('"', "")

    if "\n" in name:
        path, stage = name.split("\n", maxsplit=1)

        for text in path_text_to_delete:
            path = path.replace(text, "")

        if path in ("", ":"):
            return f"<<FONT COLOR='{text_color}'>{stage}</FONT>>"

        return f"<<FONT COLOR='{text_color}'>{path}<BR/>{stage}</FONT>>"

    return f"<<FONT COLOR='{text_color}'>{name}</FONT>>"


def format_nodes(
    graph_old: Dot,
    path_text_to_delete: Sequence[str],
    stages_merge: Sequence[str],
    colors_random_seed: int,
) -> dict[str, dict[str, str | int]]:
    """Format and filter the nodes."""
    colors = Colors(random_seed=colors_random_seed)

    all_nodes = get_all_nodes(graph_old)
    nodes_to_add: dict[str, dict[str, str | int]] = {}

    for node in all_nodes:
        name = process_node_name(node, stages_merge=stages_merge)
        options = deepcopy(DEFAULT_NODE_OPTIONS)

        if name.endswith('.dvc"'):  # is file
            options["shape"] = "box"
            options["label"] = format_displayed_name(
                name,
                path_text_to_delete=path_text_to_delete,
            )

        else:  # is stage
            has_category = "\n" in name
            category = name.split("\n")[0] if has_category else ROOT_CATEGORY
            fillcolor = colors.get_category_color(category)
            options["fillcolor"] = fillcolor
            options["style"] = "filled"
            options["label"] = format_displayed_name(
                name,
                path_text_to_delete=path_text_to_delete,
                fillcolor=fillcolor,
            )

        if name in nodes_to_add and options != nodes_to_add[name]:
            msg = "Can't add the same node with different options"
            raise ValueError(msg)

        nodes_to_add[name] = options

        logger.debug(f"Node: {node}, Processed name: {escape_newlines(name)}, Options: {options}")

    return nodes_to_add


def format_edges(graph_old: Dot, stages_merge: Sequence[str]) -> dict[str, dict[str, str]]:
    """Format the edges."""
    edges_to_add: dict[str, dict[str, str]] = {}

    for edge in graph_old.get_edges():
        source = normalize_endpoint(edge.get_source())
        dest = normalize_endpoint(edge.get_destination())

        display_source = process_node_name(source, stages_merge=stages_merge)
        display_dest = process_node_name(dest, stages_merge=stages_merge)

        options = deepcopy(DEFAULT_EDGE_OPTIONS)
        encoded_name = encode_edge_name(display_source, display_dest)

        if encoded_name in edges_to_add and options != edges_to_add[encoded_name]:
            msg = "Can't add the same edge with different options"
            raise ValueError(msg)

        edges_to_add[encoded_name] = options

        logger.debug(
            f"Edge source: {source}, dest: {dest}, encoded name: {escape_newlines(encoded_name)},"
            f" options: {options}"
        )

    return edges_to_add


def draw_dag_image(
    dag: str,
    path_text_to_delete: Sequence[str],
    stages_merge: Sequence[str],
    colors_random_seed: int,
) -> Dot:
    """Starting from a dot file, process it and return the final dag."""
    graph_new = Dot(graph_type="digraph")
    graphs = pydot.graph_from_dot_data(dag)
    if not graphs:
        msg = "Unable to parse DAG DOT data."
        raise ValueError(msg)
    graph_old = graphs[0]

    nodes_to_add = format_nodes(
        graph_old,
        path_text_to_delete=path_text_to_delete,
        stages_merge=stages_merge,
        colors_random_seed=colors_random_seed,
    )

    for node, options in nodes_to_add.items():
        graph_new.add_node(Node(node, **options))  # ty:ignore[invalid-argument-type]

    edges_to_add = format_edges(
        graph_old,
        stages_merge=stages_merge,
    )

    for name, options in edges_to_add.items():
        source, dest = decode_edge_name(name)
        graph_new.add_edge(Edge(source, dest, **options))  # ty:ignore[invalid-argument-type]

    return graph_new


def generate_dag() -> str:
    """Generate dag from DVC."""
    dvc_path = shutil.which("dvc")

    if not dvc_path:
        msg = "DVC not found. Make sure it is installed and available on your PATH."
        raise FileNotFoundError(msg)

    try:
        return subprocess.run(  # noqa: S603
            [dvc_path, "dag", "--dot"],
            capture_output=True,
            encoding="utf-8",
            check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "The 'dvc dag --dot' command failed."
        msg = f"Failed to generate the DVC DAG: {stderr}"
        raise RuntimeError(msg) from exc


def remove_transitivies(dvc_dag: str) -> str:
    """Execute the transitive reduction with the tred command from graphviz."""
    tred_path = shutil.which("tred")
    if not tred_path:
        msg = "Graphviz 'tred' was not found. Install Graphviz and make sure it is on your PATH."
        raise FileNotFoundError(msg)

    try:
        dvc_dag_tred = subprocess.run(  # noqa: S603
            [tred_path],
            input=dvc_dag,
            capture_output=True,
            encoding="utf-8",
            check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "The 'tred' command failed."
        msg = f"Graphviz 'tred' failed while processing the DVC DAG: {stderr}"
        raise RuntimeError(msg) from exc

    return dvc_dag_tred
