MAX_CHUNK_CHARS = 6000


def clip(text, limit=MAX_CHUNK_CHARS):
    if not text:
        return ""

    text = str(text)

    if len(text) <= limit:
        return text

    return text[:limit] + "\n# ... truncated ..."


def build_search_text(parts):
    values = []

    for part in parts:
        if part is None:
            continue

        text = str(part)
        text = text.replace("_", " ")

        if text.strip():
            values.append(text)

    return "\n".join(values)


def function_chunk(file_data, function):
    file_name = file_data["file"]
    function_name = function["name"]

    node_id = f"{file_name}:{function_name}"

    calls = function.get("calls", [])

    search_text = build_search_text([
        function_name,
        file_name,
        function.get("code", ""),
        " ".join(calls)
    ])

    return {
        "chunk_id": f"chunk::{node_id}",
        "node_id": node_id,
        "type": "function",
        "file": file_name,
        "name": function_name,
        "start_line": function.get("line", 0),
        "end_line": function.get("end_line", 0),
        "loc": (
            function.get("end_line", 0)
            - function.get("line", 0)
            + 1
        ),
        "calls": calls,
        "source": clip(function.get("code", "")),
        "search_text": search_text,
    }


def class_chunk(file_data, class_data):
    file_name = file_data["file"]
    class_name = class_data["name"]

    node_id = f"{file_name}:{class_name}"

    search_text = build_search_text([
        class_name,
        file_name
    ])

    return {
        "chunk_id": f"chunk::{node_id}",
        "node_id": node_id,
        "type": "class",
        "file": file_name,
        "name": class_name,
        "start_line": class_data.get("line", 0),
        "end_line": class_data.get("line", 0),
        "loc": 0,
        "source": f"class {class_name}:",
        "search_text": search_text,
    }


def file_chunk(file_data):
    file_name = file_data["file"]

    functions = file_data.get("functions", [])
    classes = file_data.get("classes", [])
    imports = file_data.get("imports", [])

    lines = [
        f"# file {file_name}"
    ]

    if imports:
        lines.append(
            "imports: " + ", ".join(str(item) for item in imports)
        )

    if classes:
        lines.append(
            "classes: " +
            ", ".join(item["name"] for item in classes)
        )

    if functions:
        lines.append(
            "functions: " +
            ", ".join(item["name"] for item in functions)
        )

    source = "\n".join(lines)

    return {
        "chunk_id": f"chunk::{file_name}",
        "node_id": file_name,
        "type": "file",
        "file": file_name,
        "name": file_name,
        "start_line": 1,
        "end_line": file_data.get("loc", 0),
        "loc": file_data.get("loc", 0),
        "source": clip(source),
        "search_text": source.replace("_", " ").replace("/", " "),
    }


def build_chunks(parsed_files):
    chunks = []

    for file_data in parsed_files:
        for function in file_data.get("functions", []):
            chunks.append(
                function_chunk(file_data, function)
            )

        for class_data in file_data.get("classes", []):
            chunks.append(
                class_chunk(file_data, class_data)
            )

        chunks.append(
            file_chunk(file_data)
        )

    return chunks


def chunk_index(chunks):
    return {
        chunk["chunk_id"]: chunk
        for chunk in chunks
    }


def chunk_by_node(chunks):
    return {
        chunk["node_id"]: chunk
        for chunk in chunks
    }


def chunk_stats(chunks):
    counts = {
        "function": 0,
        "class": 0,
        "file": 0,
        "total": len(chunks)
    }

    for chunk in chunks:
        chunk_type = chunk["type"]

        if chunk_type in counts:
            counts[chunk_type] += 1

    return counts