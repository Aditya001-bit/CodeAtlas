from fastapi import FastAPI, UploadFile, File
import zipfile
import tempfile
import os

from parser import analyze_repository
from graph import build_graph, graph_to_json


app = FastAPI(title="CodeAtlas API")

current_graph = None


@app.get("/")
def root():
    return {"message": "CodeAtlas backend is running"}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):

    global current_graph

    with tempfile.TemporaryDirectory() as temp_dir:

        zip_path = os.path.join(temp_dir, file.filename)

        with open(zip_path, "wb") as f:
            f.write(await file.read())

        extract_path = os.path.join(temp_dir, "repo")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        parsed_files = analyze_repository(extract_path)

        current_graph = build_graph(parsed_files)

        return {
            "files": len(parsed_files),
            "nodes": len(current_graph.nodes),
            "edges": len(current_graph.edges)
        }


@app.get("/api/graph")
def get_graph():

    if current_graph is None:
        return {
            "error": "No repository analyzed yet"
        }

    return graph_to_json(current_graph)


@app.get("/api/graph/node/{node_id:path}")
def get_node(node_id: str):

    if current_graph is None:
        return {"error": "No repository analyzed yet"}

    if node_id not in current_graph.nodes:
        return {"error": "Node not found"}

    node_data = current_graph.nodes[node_id]

    callers = []
    callees = []
    dependencies = []

    for source, target, data in current_graph.edges(data=True):

        if target == node_id and data["type"] == "CALLS":
            callers.append(source)

        if source == node_id and data["type"] == "CALLS":
            callees.append(target)

        if source == node_id and data["type"] == "IMPORTS":
            dependencies.append(target)

    return {
        "id": node_id,
        **node_data,
        "callers": callers,
        "callees": callees,
        "dependencies": dependencies
    }


@app.get("/api/risk")
def get_risk():

    if current_graph is None:
        return {"error": "No repository analyzed yet"}

    risks = []

    for node_id, data in current_graph.nodes(data=True):

        if data.get("type") != "function":
            continue

        loc = data.get("loc", 0)

        callers = 0
        callees = 0

        for source, target, edge_data in current_graph.edges(data=True):

            if edge_data["type"] == "CALLS":

                if target == node_id:
                    callers += 1

                if source == node_id:
                    callees += 1

        score = 20

        if loc > 5:
            score += 20

        if callees >= 2:
            score += 30

        if callers >= 2:
            score += 20

        if score >= 60:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        reasons = []

        if loc > 5:
            reasons.append("Large function")

        if callees >= 2:
            reasons.append("Calls multiple functions")

        if callers >= 2:
            reasons.append("Used by multiple functions")

        if not reasons:
            reasons.append("Low structural complexity")

        risks.append({
            "node_id": node_id,
            "score": score,
            "level": level,
            "reasons": reasons
        })

    return risks