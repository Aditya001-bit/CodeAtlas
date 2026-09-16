import ast
import os


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []

    def visit_FunctionDef(self, node):
        calls = []

        for child in ast.walk(node):

            if isinstance(child, ast.Call):

                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)

                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "calls": calls
        })

        # Don't visit nested functions separately for now


def analyze_file(file_path):
    """Analyze one Python file using AST."""

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    functions = []
    classes = []
    imports = []

    # Functions
    visitor = FunctionVisitor()
    visitor.visit(tree)
    functions = visitor.functions

    # Add source code for each function
    source_lines = source.splitlines()

    for function in functions:

        start = function["line"] - 1
        end = function["end_line"]

        function["code"] = "\n".join(source_lines[start:end])

    # Classes and imports
    for node in ast.walk(tree):

        if isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "line": node.lineno
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                imports.append(node.module)

    return {
        "file": os.path.basename(file_path),
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "loc": len(source.splitlines())
    }


def analyze_repository(repo_path):
    """Analyze all Python files in a repository."""

    result = []

    for root, _, files in os.walk(repo_path):

        for file in files:

            if file.endswith(".py"):

                file_path = os.path.join(root, file)

                try:
                    result.append(analyze_file(file_path))

                except Exception as e:
                    print(f"Could not parse {file_path}: {e}")

    return result