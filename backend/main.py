from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

import zipfile
import tempfile
import os

from backend.parser import analyze_repository
from backend.graph import build_graph, graph_to_json

from backend.risk.feature_engineering import build_feature_table
from backend.risk.predictor import RiskPredictor
from backend.risk.gemini_explainer import explain_risk_with_gemini

from backend.rag.pipeline import CodeAtlasRAG


app = FastAPI(title="CodeAtlas API")


# ============================================================
# GLOBAL STATE
# ============================================================

current_graph = None
current_analysis = None
current_rag = None

risk_predictor = RiskPredictor()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_node_file(node_data):
    """
    Get the repository-relative file path associated
    with a graph node.
    """

    return (
        node_data.get("file")
        or node_data.get("path")
        or ""
    )


def get_node_type(node_data):
    """
    Return the graph node type.
    """

    return (
        node_data.get("type")
        or node_data.get("node_type")
        or ""
    ).lower()


def get_edge_relation(edge_data):
    """
    Get the relationship type.

    graph.py stores relationships using:
        relation="CALLS"
        relation="IMPORTS"
        relation="CONTAINS"

    'type' is also supported for backward compatibility.
    """

    return (
        edge_data.get("relation")
        or edge_data.get("type")
        or ""
    ).upper()


def is_file_node(node_data):
    """
    Identify file/module nodes.
    """

    node_type = get_node_type(node_data)

    return node_type in {
        "file",
        "module",
    }


def is_symbol_node(node_data):
    """
    Identify function/class nodes.
    """

    node_type = get_node_type(node_data)

    return node_type in {
        "function",
        "class",
        "method",
    }


def node_belongs_to_file(node_id, node_data, file_path):
    """
    Determine whether a graph node belongs to a particular file.

    File nodes use the file path itself as their node ID,
    while symbol nodes store the file path in node_data["file"].
    """

    normalized_file_path = file_path.replace(
        "\\",
        "/"
    ).lstrip("/")

    normalized_node_file = get_node_file(
        node_data
    ).replace(
        "\\",
        "/"
    ).lstrip("/")

    if normalized_node_file == normalized_file_path:
        return True

    if node_id.replace(
        "\\",
        "/"
    ).lstrip("/") == normalized_file_path:
        return True

    return False


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "CodeAtlas backend is running"
    }


# ============================================================
# ANALYZE REPOSITORY
# ============================================================

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):

    global current_graph
    global current_analysis
    global current_rag

    with tempfile.TemporaryDirectory() as temp_dir:

        # ----------------------------------------------------
        # Save uploaded ZIP
        # ----------------------------------------------------

        zip_path = os.path.join(
            temp_dir,
            file.filename
        )

        with open(zip_path, "wb") as f:
            f.write(await file.read())

        # ----------------------------------------------------
        # Extract repository
        # ----------------------------------------------------

        extract_path = os.path.join(
            temp_dir,
            "repo"
        )

        with zipfile.ZipFile(
            zip_path,
            "r"
        ) as zip_ref:

            zip_ref.extractall(extract_path)

        # ----------------------------------------------------
        # Parse repository
        # ----------------------------------------------------

        parsed_files = analyze_repository(
            extract_path
        )

        current_analysis = parsed_files

        # ----------------------------------------------------
        # Build graph
        # ----------------------------------------------------

        current_graph = build_graph(
            parsed_files
        )

        # ----------------------------------------------------
        # Build RAG
        # ----------------------------------------------------

        current_rag = CodeAtlasRAG(
            current_analysis,
            current_graph
        )

        current_rag.build()

        # ----------------------------------------------------
        # Return repository statistics
        # ----------------------------------------------------

        return {
            "files": len(parsed_files),
            "nodes": len(current_graph.nodes),
            "edges": len(current_graph.edges)
        }


# ============================================================
# GET FULL GRAPH
#
# Kept for compatibility.
# The new frontend should NOT use this endpoint for
# large repositories.
# ============================================================

@app.get("/api/graph")
def get_graph():

    if current_graph is None:
        return {
            "error": "No repository analyzed yet"
        }

    return graph_to_json(
        current_graph
    )


# ============================================================
# HIERARCHICAL GRAPH — FILE LIST
# ============================================================

@app.get("/api/graph/files")
def get_graph_files():

    if (
        current_graph is None
        or current_analysis is None
    ):
        return {
            "error": "No repository analyzed yet"
        }

    files = []

    # --------------------------------------------------------
    # Use parser output as source of truth for files.
    # --------------------------------------------------------

    seen_files = set()

    for analysis_item in current_analysis:

        file_path = analysis_item.get(
            "file",
            ""
        )

        if not file_path:
            continue

        if file_path in seen_files:
            continue

        seen_files.add(file_path)

        # ----------------------------------------------------
        # Count functions/classes belonging to this file
        # ----------------------------------------------------

        symbol_count = 0

        for node_id, node_data in current_graph.nodes(
            data=True
        ):

            node_file = get_node_file(
                node_data
            )

            if node_file != file_path:
                continue

            if is_symbol_node(node_data):
                symbol_count += 1

        files.append(
            {
                "id": file_path,
                "file": file_path,
                "name": os.path.basename(file_path),
                "type": "file",
                "symbol_count": symbol_count,
            }
        )

    files.sort(
        key=lambda item: item["file"].lower()
    )

    return {
        "files": files,
        "count": len(files)
    }


# ============================================================
# HIERARCHICAL GRAPH — FILE CONTENT
#
# Returns:
#   - selected file
#   - functions/classes inside file
#   - CONTAINS relationships
#   - CALLS relationships
#   - IMPORTS relationships
#
# Imported files are included as lightweight nodes.
# ============================================================

@app.get("/api/graph/file/{file_path:path}")
def get_file_graph(file_path: str):

    if current_graph is None:
        return {
            "error": "No repository analyzed yet"
        }

    # --------------------------------------------------------
    # Normalize path
    # --------------------------------------------------------

    file_path = file_path.replace(
        "\\",
        "/"
    ).lstrip("/")

    # --------------------------------------------------------
    # Find nodes belonging to this file
    # --------------------------------------------------------

    file_node_ids = set()
    symbol_node_ids = set()

    for node_id, node_data in current_graph.nodes(
        data=True
    ):

        if not node_belongs_to_file(
            node_id,
            node_data,
            file_path
        ):
            continue

        if is_file_node(node_data):
            file_node_ids.add(node_id)

        elif is_symbol_node(node_data):
            symbol_node_ids.add(node_id)

    # --------------------------------------------------------
    # File not found
    # --------------------------------------------------------

    if not file_node_ids and not symbol_node_ids:

        return {
            "error": "File not found",
            "file": file_path
        }

    # --------------------------------------------------------
    # All nodes that belong to selected file
    # --------------------------------------------------------

    selected_node_ids = (
        file_node_ids
        | symbol_node_ids
    )

    # The graph uses the file path itself as the file node ID.
    if current_graph.has_node(file_path):
        selected_node_ids.add(file_path)
        file_node_ids.add(file_path)

    # --------------------------------------------------------
    # Build initial nodes
    # --------------------------------------------------------

    nodes_by_id = {}

    for node_id in selected_node_ids:

        if node_id not in current_graph.nodes:
            continue

        node_data = current_graph.nodes[
            node_id
        ]

        nodes_by_id[node_id] = {
            "id": node_id,
            **node_data,
        }

    # --------------------------------------------------------
    # Build relationships
    #
    # We include:
    #
    # 1. File -> Function/Class
    #       CONTAINS
    #
    # 2. Function -> Function
    #       CALLS
    #
    # 3. File -> Imported File
    #       IMPORTS
    #
    # 4. Incoming IMPORTS
    #       Other File -> Selected File
    #
    # We intentionally do NOT create fake runtime relationships.
    # --------------------------------------------------------

    edges = []

    for source, target, data in current_graph.edges(
        data=True
    ):

        relation = get_edge_relation(
            data
        )

        source_selected = (
            source in selected_node_ids
        )

        target_selected = (
            target in selected_node_ids
        )

        # ----------------------------------------------------
        # CONTAINS
        #
        # File -> Function/Class inside selected file
        # ----------------------------------------------------

        if relation == "CONTAINS":

            if (
                source_selected
                and target_selected
            ):

                edges.append(
                    {
                        "source": source,
                        "target": target,
                        **data,
                    }
                )

        # ----------------------------------------------------
        # CALLS
        #
        # Function -> Function
        # ----------------------------------------------------

        elif relation == "CALLS":

            if (
                source_selected
                and target_selected
            ):

                edges.append(
                    {
                        "source": source,
                        "target": target,
                        **data,
                    }
                )

        # ----------------------------------------------------
        # IMPORTS
        #
        # Selected file -> imported file
        #
        # Also include:
        # other file -> selected file
        # ----------------------------------------------------

        elif relation == "IMPORTS":

            if (
                source in selected_node_ids
                or target in selected_node_ids
            ):

                edges.append(
                    {
                        "source": source,
                        "target": target,
                        **data,
                    }
                )

                # Add external imported file as lightweight node
                for related_id in [
                    source,
                    target
                ]:

                    if related_id in nodes_by_id:
                        continue

                    if related_id not in current_graph.nodes:
                        continue

                    related_data = current_graph.nodes[
                        related_id
                    ]

                    if is_file_node(
                        related_data
                    ):

                        nodes_by_id[related_id] = {
                            "id": related_id,
                            **related_data,
                        }

    # --------------------------------------------------------
    # Convert nodes dictionary to list
    # --------------------------------------------------------

    nodes = list(
        nodes_by_id.values()
    )

    # --------------------------------------------------------
    # Remove duplicate edges
    # --------------------------------------------------------

    unique_edges = []
    seen_edges = set()

    for edge in edges:

        edge_key = (
            edge["source"],
            edge["target"],
            get_edge_relation(edge)
        )

        if edge_key in seen_edges:
            continue

        seen_edges.add(edge_key)

        unique_edges.append(
            edge
        )

    return {
        "file": file_path,
        "nodes": nodes,
        "edges": unique_edges,
        "symbol_count": len(symbol_node_ids)
    }


# ============================================================
# GET GRAPH NODE DETAILS
# ============================================================

@app.get("/api/graph/node/{node_id:path}")
def get_node(node_id: str):

    if current_graph is None:
        return {
            "error": "No repository analyzed yet"
        }

    if node_id not in current_graph.nodes:
        return {
            "error": "Node not found"
        }

    node_data = current_graph.nodes[
        node_id
    ]

    callers = []
    callees = []
    dependencies = []
    contained_nodes = []

    # --------------------------------------------------------
    # Find relationships
    # --------------------------------------------------------

    for source, target, data in current_graph.edges(
        data=True
    ):

        relation = get_edge_relation(
            data
        )

        # ----------------------------------------------------
        # Who calls this node?
        # ----------------------------------------------------

        if (
            target == node_id
            and relation == "CALLS"
        ):

            callers.append(
                source
            )

        # ----------------------------------------------------
        # What does this node call?
        # ----------------------------------------------------

        if (
            source == node_id
            and relation == "CALLS"
        ):

            callees.append(
                target
            )

        # ----------------------------------------------------
        # What does this node import?
        # ----------------------------------------------------

        if (
            source == node_id
            and relation == "IMPORTS"
        ):

            dependencies.append(
                target
            )

        # ----------------------------------------------------
        # What does this file contain?
        # ----------------------------------------------------

        if (
            source == node_id
            and relation == "CONTAINS"
        ):

            contained_nodes.append(
                target
            )

    # --------------------------------------------------------
    # Build LOCAL GRAPH
    #
    # Selected node + direct relationships.
    # --------------------------------------------------------

    related_ids = set(
        [node_id]
        + callers
        + callees
        + dependencies
        + contained_nodes
    )

    related_nodes = []

    for related_id in related_ids:

        if related_id not in current_graph.nodes:
            continue

        related_data = current_graph.nodes[
            related_id
        ]

        related_nodes.append(
            {
                "id": related_id,
                **related_data,
            }
        )

    local_edges = []

    for source, target, data in current_graph.edges(
        data=True
    ):

        relation = get_edge_relation(
            data
        )

        if (
            source in related_ids
            and target in related_ids
        ):

            local_edges.append(
                {
                    "source": source,
                    "target": target,
                    **data,
                }
            )

    return {
        "id": node_id,
        **node_data,

        "callers": callers,
        "callees": callees,
        "dependencies": dependencies,
        "contained_nodes": contained_nodes,

        "local_graph": {
            "nodes": related_nodes,
            "edges": local_edges,
        },
    }


# ============================================================
# RISK PREDICTIONS
# ============================================================

@app.get("/api/risk")
def get_risk():

    if (
        current_graph is None
        or current_analysis is None
    ):
        return {
            "error": "No repository analyzed yet"
        }

    # --------------------------------------------------------
    # Build ML feature table
    # --------------------------------------------------------

    feature_rows = build_feature_table(
        current_analysis,
        current_graph
    )

    # --------------------------------------------------------
    # Random Forest prediction
    # --------------------------------------------------------

    predictions = risk_predictor.predict(
        feature_rows
    )

    return predictions


# ============================================================
# GEMINI RISK EXPLANATION
# ============================================================

@app.get("/api/risk/explain/{node_id:path}")
def explain_risk(node_id: str):

    if (
        current_graph is None
        or current_analysis is None
    ):
        return {
            "error": "No repository analyzed yet"
        }

    # --------------------------------------------------------
    # Build feature table
    # --------------------------------------------------------

    feature_rows = build_feature_table(
        current_analysis,
        current_graph
    )

    # --------------------------------------------------------
    # Get Random Forest predictions
    # --------------------------------------------------------

    predictions = risk_predictor.predict(
        feature_rows
    )

    # --------------------------------------------------------
    # Find requested node
    # --------------------------------------------------------

    prediction = next(
        (
            item
            for item in predictions
            if item["id"] == node_id
        ),
        None
    )

    if prediction is None:
        return {
            "error": "Risk prediction not found"
        }

    # --------------------------------------------------------
    # Ask Gemini to explain the prediction
    #
    # IMPORTANT:
    # Random Forest decides the risk.
    # Gemini ONLY explains it.
    # --------------------------------------------------------

    explanation = explain_risk_with_gemini(

        function_name=prediction.get(
            "function"
        ),

        file_name=prediction.get(
            "file"
        ),

        risk_level=prediction.get(
            "risk_level"
        ),

        risk_probability=prediction.get(
            "risk_probability"
        ),

        reasons=prediction.get(
            "reasons",
            []
        ),

        top_features=prediction.get(
            "top_features",
            []
        ),
    )

    # --------------------------------------------------------
    # Return complete result
    # --------------------------------------------------------

    return {
        **prediction,

        "explanation": explanation.get(
            "explanation"
        ),

        "gemini_available": explanation.get(
            "gemini_available",
            False
        ),

        "error": explanation.get(
            "error"
        ),
    }


# ============================================================
# ASK CODEBASE
# ============================================================

class AskRequest(BaseModel):

    question: str


@app.post("/api/ask")
def ask_codebase(
    request: AskRequest
):

    if current_rag is None:
        return {
            "error": "No repository analyzed yet"
        }

    return current_rag.ask(
        request.question
    )