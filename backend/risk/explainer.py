from typing import Dict, List, Any

import numpy as np
import pandas as pd
import shap


# ============================================================
# FEATURE LABELS
# ============================================================

FEATURE_LABELS = {
    "loc": "function size",
    "complexity": "code complexity",
    "max_nesting": "nesting depth",
    "num_args": "function arguments",
    "num_returns": "return statements",
    "num_calls": "function calls",
    "file_imports": "file imports",
    "caller_count": "incoming callers",
    "callee_count": "outgoing callees",
    "degree": "graph connectivity",
    "betweenness": "graph centrality",
    "pagerank": "PageRank",
}


# ============================================================
# RISK CALIBRATION
# ============================================================

LOW_MAX = 0.05
MEDIUM_MAX = 0.10

HIGH_SCORE_START = 75.0
MEDIUM_SCORE_START = 50.0
LOW_SCORE_MAX = 50.0


# ============================================================
# GLOBAL MODEL IMPORTANCE
# ============================================================

def get_feature_importances(
    model,
    features: List[str],
) -> Dict[str, float]:
    """
    Return global Random Forest feature importances.

    These describe the model globally.

    They are NOT used as the primary explanation mechanism.
    SHAP is used for instance-specific explanations.
    """

    if not hasattr(model, "feature_importances_"):
        return {}

    return {
        feature: float(importance)
        for feature, importance in zip(
            features,
            model.feature_importances_,
        )
    }


# ============================================================
# VALUE HELPERS
# ============================================================

def _numeric(value: Any):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _format_value(
    feature: str,
    value: float,
) -> str:

    if feature in {
        "loc",
        "complexity",
        "max_nesting",
        "num_args",
        "num_returns",
        "num_calls",
        "file_imports",
        "caller_count",
        "callee_count",
        "degree",
    }:
        return str(int(round(value)))

    if feature == "betweenness":
        return f"{value:.3f}"

    if feature == "pagerank":
        return f"{value:.4f}"

    return f"{value:.2f}"


# ============================================================
# SHAP
# ============================================================

def _get_shap_values(
    model,
    feature_row: Dict[str, Any],
    features: List[str],
):
    """
    Calculate SHAP contributions for one function.

    Each contribution represents how a feature pushed the
    Random Forest prediction for THIS PARTICULAR function.
    """

    values = {}

    try:
        row = {}

        for feature in features:
            value = _numeric(
                feature_row.get(feature)
            )

            if value is None:
                value = 0.0

            row[feature] = value

        X = pd.DataFrame(
            [row],
            columns=features,
        )

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # SHAP output differs slightly between versions.
        #
        # For binary classification we want the contribution
        # toward class 1 = risky.

        if isinstance(shap_values, list):

            if len(shap_values) >= 2:
                values_array = np.asarray(
                    shap_values[1]
                )[0]
            else:
                values_array = np.asarray(
                    shap_values[0]
                )[0]

        else:

            values_array = np.asarray(
                shap_values
            )

            # Newer SHAP versions may return:
            # (samples, features, classes)
            if values_array.ndim == 3:

                if values_array.shape[-1] >= 2:
                    values_array = values_array[
                        0,
                        :,
                        1,
                    ]
                else:
                    values_array = values_array[
                        0,
                        :,
                        0,
                    ]

            # Standard shape:
            # (samples, features)
            elif values_array.ndim == 2:

                values_array = values_array[0]

            # Unexpected shape
            elif values_array.ndim == 1:
                pass

            else:
                return {}

        for feature, contribution in zip(
            features,
            values_array,
        ):
            values[feature] = float(
                contribution
            )

    except Exception as error:
        print(
            f"SHAP explanation failed: {error}"
        )

    return values


# ============================================================
# INSTANCE-SPECIFIC SIGNALS
# ============================================================

def _build_function_profile(
    feature_row: Dict[str, Any],
    model,
    features: List[str],
):
    """
    Build an explanation for ONE function.

    Unlike the previous implementation, this does not simply
    select globally important features.

    SHAP calculates the contribution of every feature for the
    current function.

    Positive contribution:
        pushes the prediction toward risk.

    Negative contribution:
        pushes the prediction away from risk.
    """

    shap_values = _get_shap_values(
        model=model,
        feature_row=feature_row,
        features=features,
    )

    candidates = []

    for feature in features:

        value = _numeric(
            feature_row.get(feature)
        )

        if value is None:
            value = 0.0

        contribution = float(
            shap_values.get(
                feature,
                0.0,
            )
        )

        candidates.append(
            {
                "feature": feature,
                "value": value,
                "contribution": contribution,
                "absolute_contribution": abs(
                    contribution
                ),
            }
        )

    # Sort by actual local contribution.
    candidates.sort(
        key=lambda item: item[
            "absolute_contribution"
        ],
        reverse=True,
    )

    return candidates


# ============================================================
# SHAP SIGNAL TEXT
# ============================================================

def _shap_signal_text(
    feature: str,
    value: float,
    contribution: float,
) -> str:

    label = FEATURE_LABELS.get(
        feature,
        feature.replace("_", " "),
    )

    formatted = _format_value(
        feature,
        value,
    )

    if contribution > 0:
        return (
            f"{label.capitalize()} "
            f"({formatted}) increased predicted risk"
        )

    return (
        f"{label.capitalize()} "
        f"({formatted}) reduced predicted risk"
    )


# ============================================================
# RISK SCORE
# ============================================================

def probability_to_risk_score(
    probability: float,
) -> float:
    """
    Convert Random Forest probability into the CodeAtlas
    0-100 Risk Index.

    This is a presentation index.

    It does NOT modify the underlying model probability.
    """

    probability = max(
        0.0,
        min(
            float(probability),
            1.0,
        ),
    )

    # --------------------------------------------------------
    # LOW
    # 0% -> 0
    # 5% -> 50
    # --------------------------------------------------------

    if probability < LOW_MAX:

        score = (
            probability / LOW_MAX
        ) * LOW_SCORE_MAX

        return round(
            score,
            2,
        )

    # --------------------------------------------------------
    # MEDIUM
    # 5% -> 50
    # 10% -> 75
    # --------------------------------------------------------

    if probability < MEDIUM_MAX:

        progress = (
            probability - LOW_MAX
        ) / (
            MEDIUM_MAX - LOW_MAX
        )

        score = (
            MEDIUM_SCORE_START
            + progress
            * (
                HIGH_SCORE_START
                - MEDIUM_SCORE_START
            )
        )

        return round(
            score,
            2,
        )

    # --------------------------------------------------------
    # HIGH
    # 10% -> 75
    # 20%+ -> 100
    # --------------------------------------------------------

    high_range = (
        0.20 - MEDIUM_MAX
    )

    progress = (
        probability - MEDIUM_MAX
    ) / high_range

    progress = max(
        0.0,
        min(
            progress,
            1.0,
        ),
    )

    score = (
        HIGH_SCORE_START
        + progress
        * (
            100.0
            - HIGH_SCORE_START
        )
    )

    return round(
        score,
        2,
    )


# ============================================================
# MAIN EXPLANATION FUNCTION
# ============================================================

def explain_prediction(
    feature_row: Dict[str, Any],
    feature_importances: Dict[str, float],
    risk_probability: float,
    model=None,
    features: List[str] = None,
) -> Dict[str, Any]:
    """
    Generate the CodeAtlas risk explanation.

    Random Forest:
        determines risk probability.

    SHAP:
        explains the individual prediction.

    Risk Index:
        provides the 0-100 UI representation.
    """

    probability = float(
        risk_probability
    )

    # --------------------------------------------------------
    # RISK LEVEL
    # --------------------------------------------------------

    if probability >= 0.10:
        level = "High"

    elif probability >= 0.05:
        level = "Medium"

    else:
        level = "Low"

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    if features is None:

        features = list(
            feature_importances.keys()
        )

    # --------------------------------------------------------
    # INSTANCE-SPECIFIC SHAP PROFILE
    # --------------------------------------------------------

    if model is not None:

        selected = _build_function_profile(
            feature_row=feature_row,
            model=model,
            features=features,
        )

    else:

        # Safety fallback.
        selected = []

        for feature in features:

            value = _numeric(
                feature_row.get(feature)
            )

            if value is None:
                value = 0.0

            selected.append(
                {
                    "feature": feature,
                    "value": value,
                    "contribution": 0.0,
                    "absolute_contribution": 0.0,
                }
            )

    # --------------------------------------------------------
    # TOP FEATURES
    # --------------------------------------------------------

    top_features = []

    for item in selected[:5]:

        feature = item["feature"]

        top_features.append(
            {
                "feature": feature,
                "label": FEATURE_LABELS.get(
                    feature,
                    feature.replace(
                        "_",
                        " ",
                    ),
                ),
                "value": item["value"],
                "importance": round(
                    item[
                        "absolute_contribution"
                    ],
                    4,
                ),
                "contribution": round(
                    item[
                        "contribution"
                    ],
                    4,
                ),
                "direction": (
                    "increases risk"
                    if item[
                        "contribution"
                    ] > 0
                    else "reduces risk"
                ),
            }
        )

    # --------------------------------------------------------
    # INSTANCE-SPECIFIC SIGNALS
    # --------------------------------------------------------

    reasons = []

    # We only call something a risk signal when its SHAP
    # contribution actually pushes toward risk.

    positive_features = [
        item
        for item in selected
        if item["contribution"] > 0
    ]

    positive_features.sort(
        key=lambda item: item[
            "contribution"
        ],
        reverse=True,
    )

    for item in positive_features[:3]:

        reasons.append(
            _shap_signal_text(
                feature=item["feature"],
                value=item["value"],
                contribution=item[
                    "contribution"
                ],
            )
        )

    # --------------------------------------------------------
    # FALLBACK FOR FUNCTIONS WITH NO POSITIVE SIGNAL
    # --------------------------------------------------------

    if not reasons:

        if selected:

            strongest = selected[0]

            label = FEATURE_LABELS.get(
                strongest["feature"],
                strongest["feature"].replace(
                    "_",
                    " ",
                ),
            )

            formatted = _format_value(
                strongest["feature"],
                strongest["value"],
            )

            reasons.append(
                f"No major risk-driving signal detected; "
                f"strongest local feature was "
                f"{label} ({formatted})."
            )

        else:

            reasons.append(
                "No strong risk-driving signals detected."
            )

    reasons = reasons[:3]

    # --------------------------------------------------------
    # RISK INDEX
    # --------------------------------------------------------

    risk_score = probability_to_risk_score(
        probability
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "risk_level": level,

        # Actual Random Forest probability.
        # Kept internally for transparency/debugging.
        "risk_probability": round(
            probability,
            4,
        ),

        # CodeAtlas 0-100 presentation index.
        "risk_score": risk_score,

        # Function-specific SHAP signals.
        "reasons": reasons,

        # Detailed local feature contributions.
        "top_features": top_features,
    }