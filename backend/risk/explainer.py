from __future__ import annotations

from typing import Dict, List


FEATURE_LABELS = {
    "loc": "large function size",
    "complexity": "high code complexity",
    "max_nesting": "deep nesting",
    "num_args": "many function arguments",
    "num_returns": "many return statements",
    "num_calls": "many function calls",
    "file_imports": "many file imports",
    "caller_count": "many callers",
    "callee_count": "many callees",
    "degree": "high graph connectivity",
    "betweenness": "high graph centrality",
    "pagerank": "high PageRank",
}


def explain_prediction(
    feature_row: Dict,
    feature_importances: Dict[str, float],
    risk_probability: float,
) -> Dict:

    contributions = []

    for feature, importance in feature_importances.items():

        value = feature_row.get(feature, 0)

        if value is None:
            value = 0

        if value <= 0:
            continue

        contributions.append(
            {
                "feature": feature,
                "label": FEATURE_LABELS.get(
                    feature,
                    feature,
                ),
                "value": float(value),
                "importance": float(importance),
            }
        )

    contributions.sort(
        key=lambda x: x["importance"],
        reverse=True,
    )

    top_contributions = contributions[:4]

    reasons = [
        item["label"]
        for item in top_contributions
    ]

    if risk_probability >= 0.70:
        level = "High"
    elif risk_probability >= 0.40:
        level = "Medium"
    else:
        level = "Low"

    if not reasons:
        summary = (
            "The model did not identify strong "
            "structural or graph signals."
        )
    elif len(reasons) == 1:
        summary = (
            f"The function is flagged because of "
            f"{reasons[0]}."
        )
    else:
        summary = (
            "The function is flagged primarily because of "
            + ", ".join(reasons[:-1])
            + f", and {reasons[-1]}."
        )

    return {
        "risk_level": level,
        "risk_probability": round(
            risk_probability,
            4,
        ),
        "risk_score": round(
            risk_probability * 100,
            2,
        ),
        "summary": summary,
        "reasons": reasons,
        "top_features": top_contributions,
    }


def get_feature_importances(model, features: List[str]):
    return {
        feature: float(importance)
        for feature, importance in zip(
            features,
            model.feature_importances_,
        )
    }