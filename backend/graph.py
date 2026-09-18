import networkx as nx


def build_graph(parsed_files):
    graph = nx.DiGraph()

    for file_data in parsed_files:
        file_name = file_data["file"]

        graph.add_node(
            file_name,
            type="file"
        )

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

            graph.add_edge(
                file_name,
                function_id,
                relation="CONTAINS"
            )

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
                relation="CONTAINS"
            )

    functions_by_file = {}

    for node, data in graph.nodes(data=True):
        if data.get("type") != "function":
            continue

        file_name = data["file"]
        function_name = data["name"]

        functions_by_file.setdefault(
            file_name,
            {}
        )

        functions_by_file[file_name][
            function_name
        ] = node

    for file_data in parsed_files:
        file_name = file_data["file"]

        for imported_module in file_data["imports"]:
            module_parts = imported_module.split(".")

            possible_files = [
                imported_module.replace(".", "/") + ".py",
                "/".join(module_parts) + "/__init__.py",
                module_parts[-1] + ".py"
            ]

            for imported_file in possible_files:
                if graph.has_node(imported_file):
                    graph.add_edge(
                        file_name,
                        imported_file,
                        relation="IMPORTS"
                    )
                    break

        local_functions = functions_by_file.get(
            file_name,
            {}
        )

        for function in file_data["functions"]:
            source = (
                f"{file_name}:{function['name']}"
            )

            for called_function in function["calls"]:

                target = local_functions.get(
                    called_function
                )

                if target and target != source:
                    graph.add_edge(
                        source,
                        target,
                        relation="CALLS"
                    )

    return graph


def graph_to_json(graph):
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