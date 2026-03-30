import shutil
import subprocess

from copy import deepcopy

import pydot

from pydot.core import Dot, Edge, Node

from dvc_dag.colors import Colors, needs_white_text
from dvc_dag.logger import logger


ROOT_CATEGORY = "root"
EDGE_NAME_SEPARATOR = "***"
DEFAULT_NODE_OPTIONS = {"fontsize": 20, "penwidth": "2", "fontname": "Cambria"}
DEFAULT_EDGE_OPTIONS = {"penwidth": "2"}


def get_all_nodes(graph: Dot) -> list[str]:
    """Return the list of nodes in the graph."""
    edges = graph.get_edge_list()

    connected_nodes = [(edge.get_source(), edge.get_destination()) for edge in edges]
    connected_nodes = [name for names in connected_nodes for name in names]
    connected_nodes = list(dict.fromkeys(connected_nodes))

    unconnected_nodes = [node.get_name() for node in graph.get_nodes()]
    unconnected_nodes = [node for node in unconnected_nodes if not node.endswith('.dvc"')]

    return unconnected_nodes + connected_nodes


def process_node_name(name: str, stages_merge: tuple[str]) -> str:
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


def decode_edge_name(name: str) -> list[str]:
    """Decode the edge name."""
    return name.split(EDGE_NAME_SEPARATOR)


def escape_newlines(txt: str) -> str:
    """Return a string with escaped newlines."""
    return txt.replace("\n", "\\n")


def format_displayed_name(
    name: str,
    path_text_to_delete: tuple[str],
    fillcolor: str | None = None,
) -> str:
    """Format the name shown in the node.

    For the possible attributes: https://www.graphviz.org/doc/info/shapes.html
    """
    text_color = "white" if fillcolor and needs_white_text(fillcolor) else "black"

    name = name.replace('"', "")

    if "\n" in name:
        path = name.split("\n")[0]
        stage = name.split("\n")[1]

        for text in path_text_to_delete:
            path = path.replace(text, "")

        if path in ("", ":"):
            return f"<<FONT COLOR='{text_color}'>{stage}</FONT>>"

        return f"<<FONT COLOR='{text_color}'>{path}<BR/>{stage}</FONT>>"

    return f"<<FONT COLOR='{text_color}'>{name}</FONT>>"


def format_nodes(
    graph_old: Dot,
    path_text_to_delete: list[str],
    stages_merge: list[str],
    colors_random_seed: int,
) -> dict[str, dict]:
    """Format and filter the nodes."""
    colors = Colors(random_seed=colors_random_seed)

    all_nodes = get_all_nodes(graph_old)
    nodes_to_add: dict[str, dict] = {}

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


def format_edges(graph_old: Dot, stages_merge: tuple[str]) -> dict[str, dict]:
    """Format the edges."""
    edges_to_add: dict[str, dict] = {}

    for edge in graph_old.get_edges():
        source = edge.get_source()
        dest = edge.get_destination()

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
    path_text_to_delete: list[str],
    stages_merge: list[str],
    colors_random_seed: int,
) -> Dot:
    """Starting from a dot file, process it and return the final dag."""
    graph_new = Dot(graph_type="digraph")
    graph_old: Dot = pydot.graph_from_dot_data(dag)[0]

    nodes_to_add = format_nodes(
        graph_old,
        path_text_to_delete=path_text_to_delete,
        stages_merge=stages_merge,
        colors_random_seed=colors_random_seed,
    )

    for node, options in nodes_to_add.items():
        graph_new.add_node(Node(node, **options))

    edges_to_add = format_edges(
        graph_old,
        stages_merge=stages_merge,
    )

    for name, options in edges_to_add.items():
        source, dest = decode_edge_name(name)
        graph_new.add_edge(Edge(source, dest, **options))

    return graph_new


def generate_dag() -> str:
    """Generate dag from DVC."""
    dvc_path = shutil.which("dvc")

    if not dvc_path:
        msg = "DVC not found. Make sure it's installed and reacheable via poetry or uv."
        raise FileNotFoundError(msg)

    return subprocess.run(  # noqa: S603
        [dvc_path, "dag", "--dot"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    ).stdout


def remove_transitivies(dvc_dag: str) -> str:
    """Execute the transitive reduction with the tred command from graphviz."""
    try:
        dvc_dag_tred = subprocess.run(
            ["tred"],  # noqa: S607
            input=dvc_dag,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
        ).stdout
    except Exception as exc:
        msg = (
            "Error: 'tred' command failed — Graphviz may not be installed."
            " Try: `brew install graphviz` (https://www.graphviz.org/download/)"
        )
        raise RuntimeError(msg) from exc

    return dvc_dag_tred
