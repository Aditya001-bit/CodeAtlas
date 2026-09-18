from feature_engineering import build_feature_table
from predictor import score_repository
from backend.risk.explainer import build_explanation

import networkx as nx


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


features = build_feature_table(
    analysis,
    graph
)

results = score_repository(
    features
)

explanation = build_explanation(
    results[0]
)

print("\nEXPLANATION")
print(explanation)

assert "function" in explanation
assert "risk_score" in explanation
assert "risk_level" in explanation
assert "summary" in explanation
assert "reasons" in explanation
assert "factors" in explanation

print("\n✅ ALL EXPLANATION TESTS PASSED")