from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

import zipfile
import tempfile
import os

from backend.parser import analyze_repository
from backend.graph import build_graph, graph_to_json

from backend.risk.feature_engineering import build_raw_features
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
async def analyze(
    file: UploadFile = File(...)
):

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

        with open(
            zip_path,
            "wb"
        ) as f:

            f.write(
                await file.read()
            )

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

            zip_ref.extractall(
                extract_path
            )

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
            "files": len(
                parsed_files
            ),
            "nodes": len(
                current_graph.nodes
            ),
            "edges": len(
                current_graph.edges
            )
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
#
# This is the first endpoint used by the new Code Map.
#
# IMPORTANT:
# It returns only repository files.
# It does NOT return thousands of graph nodes.
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
    # Use parser output as the source of truth for files.
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

        seen_files.add(
            file_path
        )

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

            if is_symbol_node(
                node_data
            ):

                symbol_count += 1

        files.append(
            {
                "id": file_path,
                "file": file_path,
                "name": os.path.basename(
                    file_path
                ),
                "type": "file",
                "symbol_count": symbol_count,
            }
        )

    files.sort(
        key=lambda item:
        item["file"].lower()
    )

    return {
        "files": files,
        "count": len(files)
    }


# ============================================================
# HIERARCHICAL GRAPH — FILE CONTENT
#
# Returns only the symbols inside ONE file.
#
# The frontend calls this after the user selects a file.
# ============================================================

@app.get("/api/graph/file/{file_path:path}")
def get_file_graph(
    file_path: str
):

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

    file_nodes = []
    symbol_node_ids = set()

    for node_id, node_data in current_graph.nodes(
        data=True
    ):

        node_file = get_node_file(
            node_data
        )

        normalized_node_file = (
            node_file
            .replace("\\", "/")
            .lstrip("/")
        )

        if normalized_node_file != file_path:
            continue

        # ----------------------------------------------------
        # File/module node
        # ----------------------------------------------------

        if is_file_node(
            node_data
        ):

            file_nodes.append(
                {
                    "id": node_id,
                    **node_data,
                }
            )

        # ----------------------------------------------------
        # Function/class node
        # ----------------------------------------------------

        elif is_symbol_node(
            node_data
        ):

            symbol_node_ids.add(
                node_id
            )

    # --------------------------------------------------------
    # File not found
    # --------------------------------------------------------

    if (
        not file_nodes
        and not symbol_node_ids
    ):

        return {
            "error": "File not found",
            "file": file_path
        }

    # --------------------------------------------------------
    # Build symbol nodes
    # --------------------------------------------------------

    nodes = []

    for node_id in symbol_node_ids:

        node_data = current_graph.nodes[
            node_id
        ]

        nodes.append(
            {
                "id": node_id,
                **node_data,
            }
        )

    # --------------------------------------------------------
    # Add file node if available
    # --------------------------------------------------------

    nodes = (
        file_nodes
        + nodes
    )

    # --------------------------------------------------------
    # Only include relationships INSIDE this file.
    #
    # This keeps the graph small.
    # --------------------------------------------------------

    edges = []

    for source, target, data in current_graph.edges(
        data=True
    ):

        if (
            source in symbol_node_ids
            and target in symbol_node_ids
        ):

            edges.append(
                {
                    "source": source,
                    "target": target,
                    **data,
                }
            )

    return {
        "file": file_path,
        "nodes": nodes,
        "edges": edges,
        "symbol_count": len(
            symbol_node_ids
        )
    }


# ============================================================
# GET GRAPH NODE DETAILS
# ============================================================

@app.get("/api/graph/node/{node_id:path}")
def get_node(
    node_id: str
):

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

    # --------------------------------------------------------
    # Find relationships
    # --------------------------------------------------------

    for source, target, data in current_graph.edges(
        data=True
    ):

        edge_type = data.get(
            "type"
        )

        # ----------------------------------------------------
        # Who calls this node?
        # ----------------------------------------------------

        if (
            target == node_id
            and edge_type == "CALLS"
        ):

            callers.append(
                source
            )

        # ----------------------------------------------------
        # What does this node call?
        # ----------------------------------------------------

        if (
            source == node_id
            and edge_type == "CALLS"
        ):

            callees.append(
                target
            )

        # ----------------------------------------------------
        # What does this node import?
        # ----------------------------------------------------

        if (
            source == node_id
            and edge_type == "IMPORTS"
        ):

            dependencies.append(
                target
            )

    # --------------------------------------------------------
    # Build LOCAL GRAPH
    #
    # Only selected node + direct callers/callees/dependencies.
    #
    # This is intentionally tiny compared with the complete
    # repository graph.
    # --------------------------------------------------------

    related_ids = set(
        [node_id]
        + callers
        + callees
        + dependencies
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
    # IMPORTANT:
    #
    # Use RAW features here.
    #
    # Do NOT use build_feature_table(), because that function
    # adds percentile-normalized features.
    #
    # The final production model already performs:
    #
    # raw features
    #      ↓
    # StandardScaler
    #      ↓
    # Logistic Regression
    #      ↓
    # Isotonic calibration
    #
    # This must match the production training pipeline.
    # --------------------------------------------------------

    feature_rows = build_raw_features(
        current_analysis,
        current_graph
    )

    # --------------------------------------------------------
    # FINAL PRODUCTION MODEL
    #
    # Logistic Regression + Isotonic Calibration
    # --------------------------------------------------------

    predictions = risk_predictor.predict(
        feature_rows
    )

    return predictions


# ============================================================
# GEMINI RISK EXPLANATION
# ============================================================

@app.get("/api/risk/explain/{node_id:path}")
def explain_risk(
    node_id: str
):

    if (
        current_graph is None
        or current_analysis is None
    ):

        return {
            "error": "No repository analyzed yet"
        }

    # --------------------------------------------------------
    # Use the EXACT same raw features as /api/risk.
    # --------------------------------------------------------

    feature_rows = build_raw_features(
        current_analysis,
        current_graph
    )

    # --------------------------------------------------------
    # Get FINAL ML predictions
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
    # Gemini ONLY explains the ML prediction.
    #
    # Gemini does NOT determine risk.
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