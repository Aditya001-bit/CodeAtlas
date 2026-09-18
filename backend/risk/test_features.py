import networkx as nx

from feature_engineering import (
    build_raw_features,
    build_feature_table,
    feature_matrix,
)


analysis = [
    {
        "file": "auth.py",
        "imports": ["database"],
        "functions": [
            {
                "name": "login",
                "line": 1,
                "end_line": 12,
                "calls": ["check_password"],
                "source": """def login(username, password):
    user = get_user(username)
    if user:
        if check_password(password):
            return create_session(user)
    return None
""",
            },
            {
                "name": "check_password",
                "line": 14,
                "end_line": 16,
                "calls": [],
                "source": """def check_password(password):
    return password == "admin"
""",
            },
        ],
        "classes": [],
        "loc": 16,
    }
]


graph = nx.DiGraph()

graph.add_node("auth.py")
graph.add_node("auth.py:login")
graph.add_node("auth.py:check_password")

graph.add_edge(
    "auth.py",
    "auth.py:login",
    relation="CONTAINS"
)

graph.add_edge(
    "auth.py",
    "auth.py:check_password",
    relation="CONTAINS"
)

graph.add_edge(
    "auth.py:login",
    "auth.py:check_password",
    relation="CALLS"
)


rows = build_raw_features(
    analysis,
    graph
)

print("\nRAW FEATURES")
for row in rows:
    print(row)


table = build_feature_table(
    analysis,
    graph
)

print("\nFEATURE TABLE")
for row in table:
    print(row)


matrix = feature_matrix(table)

print("\nFEATURE MATRIX")
print(matrix)

print("\nShape:", matrix.shape)

assert len(rows) == 2
assert matrix.shape == (2, 13)

print("\n✅ ALL RISK FEATURE TESTS PASSED")