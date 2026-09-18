from backend.risk.dataset.function_mapper import changed_line_numbers, map_changed_lines_to_functions


def test_changed_lines_map_to_function():
    old = "def a():\n    x = 1\n\ndef b():\n    y = 2\n"
    new = "def a():\n    x = 2\n\ndef b():\n    y = 2\n"
    changed = changed_line_numbers(old, new)
    funcs = map_changed_lines_to_functions(old, changed)
    assert [(x["name"], x["line"]) for x in funcs] == [("a", 1)]
