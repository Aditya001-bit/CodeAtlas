from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Dict, List

import networkx as nx

from backend.parser import analyze_repository
from backend.graph import build_graph


FEATURES = [
    "loc",
    "complexity",
    "max_nesting",
    "num_args",
    "num_returns",
    "num_calls",
    "file_imports",
    "caller_count",
    "callee_count",
    "dependency_count",
    "degree",
    "betweenness",
    "pagerank",
]


def _source_metrics(source: str) -> Dict[str, int]:
    source = textwrap.dedent(source).strip()

    if not source:
        return {
            "loc": 0,
            "complexity": 1,
            "max_nesting": 0,
            "num_args": 0,
            "num_returns": 0,
            "num_calls": 0,
        }

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {
            "loc": len(source.splitlines()),
            "complexity": 1,
            "max_nesting": 0,
            "num_args": 0,
            "num_returns": 0,
            "num_calls": 0,
        }

    decision_nodes = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.IfExp,
        ast.Try,
        ast.ExceptHandler,
        ast.With,
        ast.AsyncWith,
    )

    nesting_nodes = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
    )

    complexity = 1
    max_depth = 0

    def walk(node, depth=0):
        nonlocal complexity
        nonlocal max_depth

        if isinstance(node, decision_nodes):
            complexity += 1

        if isinstance(node, nesting_nodes):
            depth += 1
            max_depth = max(max_depth, depth)

        for child in ast.iter_child_nodes(node):
            walk(child, depth)

    walk(tree)

    function_node = None

    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            function_node = node
            break

    if function_node is not None:
        args = function_node.args

        num_args = (
            len(args.posonlyargs)
            + len(args.args)
            + len(args.kwonlyargs)
        )

        if args.vararg is not None:
            num_args += 1

        if args.kwarg is not None:
            num_args += 1
    else:
        num_args = 0

    num_returns = sum(
        isinstance(node, ast.Return)
        for node in ast.walk(tree)
    )

    num_calls = sum(
        isinstance(node, ast.Call)
        for node in ast.walk(tree)
    )

    return {
        "loc": len(source.splitlines()),
        "complexity": complexity,
        "max_nesting": max_depth,
        "num_args": num_args,
        "num_returns": num_returns,
        "num_calls": num_calls,
    }


def _graph_metrics(graph: nx.DiGraph):
    callers = {}
    callees = {}
    dependencies = {}
    degree = {}

    for node in graph.nodes:
        callers[node] = 0
        callees[node] = 0
        dependencies[node] = 0
        degree[node] = graph.degree(node)

    for source, target, data in graph.edges(data=True):
        relation = data.get("relation")

        if relation == "CALLS":
            callees[source] += 1
            callers[target] += 1

        elif relation == "IMPORTS":
            dependencies[source] += 1

    node_count = graph.number_of_nodes()

    if node_count == 0:
        return (
            callers,
            callees,
            dependencies,
            degree,
            {},
            {},
        )

    if node_count <= 200:
        betweenness = nx.betweenness_centrality(
            graph,
            normalized=True,
        )

    else:
        sample_size = min(
            50,
            node_count,
        )

        betweenness = nx.betweenness_centrality(
            graph,
            k=sample_size,
            normalized=True,
            seed=42,
        )

    pagerank = nx.pagerank(
        graph,
        max_iter=50,
        tol=1e-4,
    )

    return (
        callers,
        callees,
        dependencies,
        degree,
        betweenness,
        pagerank,
    )


def analyze_with_features(
    repo: Path,
) -> List[Dict]:

    parsed = analyze_repository(
        str(repo)
    )

    graph = build_graph(
        parsed
    )

    (
        callers,
        callees,
        dependencies,
        degree,
        betweenness,
        pagerank,
    ) = _graph_metrics(graph)

    rows = []

    for record in parsed:

        file_name = record["file"]

        file_import_count = len(
            record.get("imports", [])
        )

        for function in record["functions"]:

            node_id = (
                f"{file_name}:"
                f"{function['name']}"
            )

            source = function.get(
                "code",
                ""
            )

            metrics = _source_metrics(
                source
            )

            rows.append(
                {
                    "id": node_id,
                    "file": file_name,
                    "function": function["name"],
                    "loc": metrics["loc"],
                    "complexity": metrics["complexity"],
                    "max_nesting": metrics["max_nesting"],
                    "num_args": metrics["num_args"],
                    "num_returns": metrics["num_returns"],
                    "num_calls": metrics["num_calls"],
                    "file_imports": file_import_count,
                    "caller_count": callers.get(
                        node_id,
                        0,
                    ),
                    "callee_count": callees.get(
                        node_id,
                        0,
                    ),
                    "dependency_count": dependencies.get(
                        node_id,
                        0,
                    ),
                    "degree": degree.get(
                        node_id,
                        0,
                    ),
                    "betweenness": betweenness.get(
                        node_id,
                        0.0,
                    ),
                    "pagerank": pagerank.get(
                        node_id,
                        0.0,
                    ),
                }
            )

    return rows