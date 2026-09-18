import ast
import networkx as nx
import numpy as np


CODE_FEATURES = [
    "loc",
    "complexity",
    "max_nesting",
    "num_args",
    "num_returns",
    "num_calls",
    "file_imports",
]

GRAPH_FEATURES = [
    "caller_count",
    "callee_count",
    "dependency_count",
    "degree",
    "betweenness",
    "pagerank",
]

ALL_FEATURES = CODE_FEATURES + GRAPH_FEATURES


def get_source_metrics(source):
    try:
        tree = ast.parse(source)
    except Exception:
        return {
            "loc": 0,
            "complexity": 1,
            "max_nesting": 0,
            "num_args": 0,
            "num_returns": 0,
            "num_calls": 0,
        }

    function_node = None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_node = node
            break

    if function_node is None:
        return {
            "loc": len(source.splitlines()),
            "complexity": 1,
            "max_nesting": 0,
            "num_args": 0,
            "num_returns": 0,
            "num_calls": 0,
        }

    loc = len(source.splitlines())

    complexity = 1

    for node in ast.walk(function_node):
        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.ExceptHandler,
                ast.With,
                ast.AsyncWith,
                ast.IfExp,
                ast.comprehension,
            ),
        ):
            complexity += 1

        if isinstance(node, ast.BoolOp):
            complexity += max(0, len(node.values) - 1)

    max_nesting = calculate_max_nesting(function_node)

    num_args = len(function_node.args.args)

    num_returns = sum(
        1
        for node in ast.walk(function_node)
        if isinstance(node, ast.Return)
    )

    num_calls = sum(
        1
        for node in ast.walk(function_node)
        if isinstance(node, ast.Call)
    )

    return {
        "loc": loc,
        "complexity": complexity,
        "max_nesting": max_nesting,
        "num_args": num_args,
        "num_returns": num_returns,
        "num_calls": num_calls,
    }


def calculate_max_nesting(function_node):
    max_depth = 0

    nesting_nodes = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
    )

    def visit(node, depth):
        nonlocal max_depth

        if isinstance(node, nesting_nodes):
            depth += 1
            max_depth = max(max_depth, depth)

        for child in ast.iter_child_nodes(node):
            visit(child, depth)

    visit(function_node, 0)

    return max_depth


def build_file_import_index(analysis):
    result = {}

    for file_data in analysis:
        file_name = file_data.get("file", "")
        imports = file_data.get("imports", [])

        result[file_name] = len(imports)

    return result


def find_function_data(analysis, node_id):
    if ":" not in node_id:
        return None

    file_name, function_name = node_id.split(":", 1)

    for file_data in analysis:
        if file_data.get("file") != file_name:
            continue

        for function in file_data.get("functions", []):
            if function.get("name") == function_name:
                return file_data, function

    return None


def calculate_graph_metrics(graph):
    if graph is None or len(graph) == 0:
        return {}

    try:
        betweenness = nx.betweenness_centrality(graph)
    except Exception:
        betweenness = {
            node: 0
            for node in graph.nodes
        }

    try:
        pagerank = nx.pagerank(graph)
    except Exception:
        pagerank = {
            node: 0
            for node in graph.nodes
        }

    metrics = {}

    for node in graph.nodes:

        callers = 0
        callees = 0
        dependencies = 0

        for source, target, data in graph.in_edges(
            node,
            data=True
        ):
            relation = data.get(
                "relation",
                data.get("type", "")
            )

            if relation == "CALLS":
                callers += 1

        for source, target, data in graph.out_edges(
            node,
            data=True
        ):
            relation = data.get(
                "relation",
                data.get("type", "")
            )

            if relation == "CALLS":
                callees += 1

            if relation == "IMPORTS":
                dependencies += 1

        metrics[node] = {
            "caller_count": callers,
            "callee_count": callees,
            "dependency_count": dependencies,
            "degree": graph.degree(node),
            "betweenness": betweenness.get(node, 0),
            "pagerank": pagerank.get(node, 0),
        }

    return metrics


def build_raw_features(analysis, graph):
    file_imports = build_file_import_index(analysis)
    graph_metrics = calculate_graph_metrics(graph)

    rows = []

    for file_data in analysis:
        file_name = file_data.get("file", "")

        for function in file_data.get("functions", []):

            function_name = function.get(
                "name",
                ""
            )

            node_id = f"{file_name}:{function_name}"

            source = function.get(
                "source",
                ""
            )

            source_metrics = get_source_metrics(
                source
            )

            graph_data = graph_metrics.get(
                node_id,
                {
                    "caller_count": 0,
                    "callee_count": 0,
                    "dependency_count": 0,
                    "degree": 0,
                    "betweenness": 0,
                    "pagerank": 0,
                },
            )

            row = {
                "id": node_id,
                "name": function_name,
                "file": file_name,
                **source_metrics,
                "file_imports": file_imports.get(
                    file_name,
                    0
                ),
                **graph_data,
            }

            rows.append(row)

    return rows


def percentile_map(values):
    values = np.asarray(
        values,
        dtype=float
    )

    if len(values) == 0:
        return values

    if len(values) == 1:
        return np.array([0.5])

    order = np.argsort(
        np.argsort(values)
    )

    return order / (len(values) - 1)


def normalize_features(rows):
    if not rows:
        return []

    normalized = [
        dict(row)
        for row in rows
    ]

    for feature in ALL_FEATURES:

        values = [
            float(row.get(feature, 0))
            for row in rows
        ]

        percentiles = percentile_map(
            values
        )

        for i, value in enumerate(
            percentiles
        ):
            normalized[i][
                f"{feature}_normalized"
            ] = float(value)

    return normalized


def build_feature_table(analysis, graph):
    raw = build_raw_features(
        analysis,
        graph
    )

    normalized = normalize_features(
        raw
    )

    return normalized


def feature_matrix(rows):
    if not rows:
        return np.empty(
            (0, len(ALL_FEATURES))
        )

    return np.array(
        [
            [
                float(
                    row.get(
                        feature,
                        0
                    )
                )
                for feature in ALL_FEATURES
            ]
            for row in rows
        ],
        dtype=float,
    )


def repository_feature_summary(rows):
    if not rows:
        return {}

    summary = {}

    for feature in ALL_FEATURES:

        values = [
            float(row.get(feature, 0))
            for row in rows
        ]

        summary[feature] = {
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
        }

    return summary