from feature_engineering import build_feature_table
from predictor import (
    score_repository,
    risk_index,
    top_risky,
    explain,
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


import networkx as nx

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


features = build_feature_table(
    analysis,
    graph
)

results = score_repository(
    features
)

print("\nRISK RESULTS")

for result in results:
    print(result)

print("\nRISK INDEX")

print(
    risk_index(results)
)

print("\nTOP RISKY")

print(
    top_risky(results)
)

print("\nEXPLANATION")

print(
    explain(results[0])
)

assert len(results) == 2

for result in results:
    assert 0 <= result["score"] <= 1
    assert result["risk_level"] in [
        "LOW",
        "MEDIUM",
        "HIGH",
    ]
    assert len(result["reasons"]) > 0

print("\n✅ ALL RISK PREDICTOR TESTS PASSED")