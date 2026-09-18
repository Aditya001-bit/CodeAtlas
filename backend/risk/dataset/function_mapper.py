from __future__ import annotations

import ast
import difflib
from pathlib import Path
from typing import Dict, Iterable, List, Set


def changed_python_files(buggy_repo: Path, fixed_repo: Path) -> List[str]:
    files: Set[str] = set()
    all_paths = set()

    for base in (buggy_repo, fixed_repo):
        for path in base.rglob("*.py"):
            if ".git" not in path.parts:
                all_paths.add(path.relative_to(base).as_posix())

    for rel in sorted(all_paths):
        before = buggy_repo / rel
        after = fixed_repo / rel

        if not before.exists() or not after.exists():
            files.add(rel)
            continue

        try:
            old = before.read_text(encoding="utf-8", errors="replace")
            new = after.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if old != new:
            files.add(rel)

    return sorted(files)


def changed_line_numbers(
    buggy_source: str,
    fixed_source: str
) -> Set[int]:
    old = buggy_source.splitlines()
    new = fixed_source.splitlines()

    matcher = difflib.SequenceMatcher(
        a=old,
        b=new,
        autojunk=False
    )

    lines: Set[int] = set()

    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag != "equal":
            if i1 == i2:
                lines.add(max(1, i1))
            else:
                lines.update(range(i1 + 1, i2 + 1))

    return lines


def function_ranges(source: str) -> List[Dict]:
    tree = ast.parse(source)

    rows = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            rows.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(
                    node,
                    "end_lineno",
                    node.lineno
                ),
            })

    return rows


def map_changed_lines_to_functions(
    source: str,
    changed_lines: Iterable[int]
) -> List[Dict]:

    changed = set(changed_lines)
    functions = function_ranges(source)

    matches = []

    for fn in functions:
        if any(
            fn["line"] <= line <= fn["end_line"]
            for line in changed
        ):
            matches.append(fn)

    return matches


def is_test_file(file_path: str) -> bool:
    path = file_path.replace("\\", "/").lower()

    parts = path.split("/")

    if "tests" in parts or "test" in parts:
        return True

    filename = parts[-1]

    return (
        filename.startswith("test_")
        or filename.endswith("_test.py")
    )


def map_bug_to_functions(
    buggy_repo: Path,
    fixed_repo: Path
) -> List[Dict]:

    positives: List[Dict] = []

    for rel in changed_python_files(
        buggy_repo,
        fixed_repo
    ):

        if is_test_file(rel):
            continue

        before = buggy_repo / rel
        after = fixed_repo / rel

        old_source = (
            before.read_text(
                encoding="utf-8",
                errors="replace"
            )
            if before.exists()
            else ""
        )

        new_source = (
            after.read_text(
                encoding="utf-8",
                errors="replace"
            )
            if after.exists()
            else ""
        )

        try:
            changed = changed_line_numbers(
                old_source,
                new_source
            )

            matches = map_changed_lines_to_functions(
                old_source,
                changed
            )

        except SyntaxError:
            matches = []

        for fn in matches:
            positives.append({
                "file": rel,
                **fn
            })

    return positives