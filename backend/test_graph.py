from parser import analyze_repository
from graph import build_graph, graph_to_json


repo = "../demo-repo"

parsed_files = analyze_repository(repo)

graph = build_graph(parsed_files)

result = graph_to_json(graph)

print("\nNODES")
for node in result["nodes"]:
    print(node)

print("\nEDGES")
for edge in result["edges"]:
    print(edge)