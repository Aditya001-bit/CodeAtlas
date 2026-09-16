import networkx as nx

def build_graph(parsed_files):
    graph = nx.DiGraph()

    # Add file, class and function nodes
    for file_data in parsed_files:
        file_name = file_data["file"]

        # File node
        graph.add_node(
            file_name,
            type="file"
        )

        # Function nodes
        for function in file_data["functions"]:
            function_id = f"{file_name}:{function['name']}"

            graph.add_node(
                function_id,
                type="function",
                name=function["name"],
                file=file_name,
                line=function["line"],
                end_line=function["end_line"],
                loc=function["end_line"] - function["line"] + 1,
                code=function["code"]
            )

            # Function belongs to file
            graph.add_edge(
                file_name,
                function_id,
                type="CONTAINS"
            )

        # Class nodes
        for class_data in file_data["classes"]:
            class_id = f"{file_name}:{class_data['name']}"

            graph.add_node(
                class_id,
                type="class",
                name=class_data["name"],
                file=file_name,
                line=class_data["line"]
            )

            graph.add_edge(
                file_name,
                class_id,
                type="CONTAINS"
            )

    # Create lookup:
    # function name -> function node
    function_lookup = {}

    for node, data in graph.nodes(data=True):
        if data.get("type") == "function":
            function_lookup[data["name"]] = node

    # Add IMPORTS and CALLS relationships
    for file_data in parsed_files:

        file_name = file_data["file"]

        # IMPORTS
        for imported_module in file_data["imports"]:

            imported_file = imported_module.split(".")[-1] + ".py"

            if graph.has_node(imported_file):
                graph.add_edge(
                    file_name,
                    imported_file,
                    type="IMPORTS"
                )

        # CALLS
        for function in file_data["functions"]:

            source = f"{file_name}:{function['name']}"

            for called_function in function["calls"]:

                target = function_lookup.get(called_function)

                if target and target != source:
                    graph.add_edge(
                        source,
                        target,
                        type="CALLS"
                    )

    return graph


def graph_to_json(graph):
    """Convert NetworkX graph into frontend-friendly JSON."""

    nodes = []

    for node_id, data in graph.nodes(data=True):
        nodes.append({
            "id": node_id,
            **data
        })

    edges = []

    for source, target, data in graph.edges(data=True):
        edges.append({
            "source": source,
            "target": target,
            **data
        })

    return {
        "nodes": nodes,
        "edges": edges
    }