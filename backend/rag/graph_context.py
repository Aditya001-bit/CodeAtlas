import networkx as nx


def node_label(node_id, data):
    node_type = data.get("type", "node")
    name = data.get("name", node_id)

    if node_type == "function":
        return f"{data.get('file', '')}:{name}"

    if node_type == "class":
        return f"{data.get('file', '')}:{name}"

    return str(name)


def get_neighbors(graph, node_id, hops=1):
    if node_id not in graph:
        return set()

    nodes = {node_id}

    current = {node_id}

    for _ in range(hops):
        next_nodes = set()

        for node in current:
            next_nodes.update(graph.predecessors(node))
            next_nodes.update(graph.successors(node))

        next_nodes -= nodes
        nodes.update(next_nodes)
        current = next_nodes

    return nodes


def relationship_text(graph, source, target):
    data = graph.get_edge_data(source, target, default={})
    return data.get("relation", "RELATED")


def build_graph_context(graph, hits, hops=1, max_nodes=30):
    if graph is None:
        return {
            "nodes": [],
            "relationships": [],
            "text": ""
        }

    selected_nodes = set()

    for hit in hits:
        node_id = hit.get("node_id")

        if node_id in graph:
            selected_nodes.update(
                get_neighbors(graph, node_id, hops)
            )

    selected_nodes = list(selected_nodes)[:max_nodes]

    nodes = []

    for node_id in selected_nodes:
        data = graph.nodes[node_id]

        nodes.append({
            "id": node_id,
            "type": data.get("type", "node"),
            "name": data.get("name", node_id),
            "file": data.get("file", node_id)
        })

    selected_set = set(selected_nodes)

    relationships = []

    for source, target in graph.edges():
        if source not in selected_set:
            continue

        if target not in selected_set:
            continue

        relation = relationship_text(
            graph,
            source,
            target
        )

        relationships.append({
            "source": source,
            "target": target,
            "relation": relation
        })

    lines = []

    for relationship in relationships:
        source_data = graph.nodes[relationship["source"]]
        target_data = graph.nodes[relationship["target"]]

        source_label = node_label(
            relationship["source"],
            source_data
        )

        target_label = node_label(
            relationship["target"],
            target_data
        )

        lines.append(
            f"{source_label} --{relationship['relation']}--> {target_label}"
        )

    return {
        "nodes": nodes,
        "relationships": relationships,
        "text": "\n".join(lines)
    }


def get_callers(graph, node_id):
    if node_id not in graph:
        return []

    callers = []

    for source in graph.predecessors(node_id):
        relation = relationship_text(
            graph,
            source,
            node_id
        )

        if relation == "CALLS":
            callers.append(source)

    return callers


def get_callees(graph, node_id):
    if node_id not in graph:
        return []

    callees = []

    for target in graph.successors(node_id):
        relation = relationship_text(
            graph,
            node_id,
            target
        )

        if relation == "CALLS":
            callees.append(target)

    return callees


def get_imports(graph, node_id):
    if node_id not in graph:
        return []

    imports = []

    for target in graph.successors(node_id):
        relation = relationship_text(
            graph,
            node_id,
            target
        )

        if relation == "IMPORTS":
            imports.append(target)

    return imports


def get_call_chain(graph, node_id, depth=3):
    if node_id not in graph:
        return []

    chain = []

    current = node_id
    visited = {current}

    for _ in range(depth):
        callees = get_callees(graph, current)

        next_node = None

        for candidate in callees:
            if candidate not in visited:
                next_node = candidate
                break

        if next_node is None:
            break

        chain.append({
            "from": current,
            "to": next_node,
            "relation": "CALLS"
        })

        visited.add(next_node)
        current = next_node

    return chain