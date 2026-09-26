from typing import Dict, List, Any

import numpy as np
import pandas as pd


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
# FINAL CODEATLAS RISK THRESHOLDS
# ============================================================

LOW_THRESHOLD = 0.20
HIGH_THRESHOLD = 0.30


# ============================================================
# GLOBAL MODEL IMPORTANCE
# ============================================================

def get_feature_importances(
    model,
    features: List[str],
) -> Dict[str, float]:
    """
    Extract global feature importance from the underlying
    Logistic Regression model.

    Production pipeline:

        StandardScaler
            ↓
        Logistic Regression
            ↓
        Isotonic Calibration

    Absolute coefficient magnitude is used as global
    model-level importance.

    These are model signals, not causal explanations.
    """

    # --------------------------------------------------------
    # Direct Logistic Regression
    # --------------------------------------------------------

    if hasattr(model, "coef_"):

        coefficients = np.asarray(
            model.coef_
        ).reshape(-1)

        return {
            feature: float(abs(coefficient))
            for feature, coefficient in zip(
                features,
                coefficients,
            )
        }

    # --------------------------------------------------------
    # CalibratedClassifierCV
    # --------------------------------------------------------

    if hasattr(
        model,
        "calibrated_classifiers_",
    ):

        fold_coefficients = []

        for calibrated_model in (
            model.calibrated_classifiers_
        ):

            estimator = getattr(
                calibrated_model,
                "estimator",
                None,
            )

            if estimator is None:

                estimator = getattr(
                    calibrated_model,
                    "base_estimator",
                    None,
                )

            if (
                estimator is not None
                and hasattr(
                    estimator,
                    "coef_",
                )
            ):

                fold_coefficients.append(
                    np.asarray(
                        estimator.coef_
                    ).reshape(-1)
                )

        if fold_coefficients:

            mean_coefficients = np.mean(
                np.vstack(
                    fold_coefficients
                ),
                axis=0,
            )

            return {
                feature: float(abs(coefficient))
                for feature, coefficient in zip(
                    features,
                    mean_coefficients,
                )
            }

    return {}


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

        return str(
            int(
                round(value)
            )
        )

    if feature == "betweenness":

        return f"{value:.3f}"

    if feature == "pagerank":

        return f"{value:.4f}"

    return f"{value:.2f}"


# ============================================================
# LOGISTIC REGRESSION COEFFICIENTS
# ============================================================

def _get_logistic_coefficients(
    model,
    features: List[str],
) -> Dict[str, float]:
    """
    Extract coefficients from the underlying Logistic
    Regression model.
    """

    # --------------------------------------------------------
    # Direct Logistic Regression
    # --------------------------------------------------------

    if hasattr(model, "coef_"):

        coefficients = np.asarray(
            model.coef_
        ).reshape(-1)

        return {
            feature: float(coefficient)
            for feature, coefficient in zip(
                features,
                coefficients,
            )
        }

    # --------------------------------------------------------
    # CalibratedClassifierCV
    # --------------------------------------------------------

    if hasattr(
        model,
        "calibrated_classifiers_",
    ):

        fold_coefficients = []

        for calibrated_model in (
            model.calibrated_classifiers_
        ):

            estimator = getattr(
                calibrated_model,
                "estimator",
                None,
            )

            if estimator is None:

                estimator = getattr(
                    calibrated_model,
                    "base_estimator",
                    None,
                )

            if (
                estimator is not None
                and hasattr(
                    estimator,
                    "coef_",
                )
            ):

                fold_coefficients.append(
                    np.asarray(
                        estimator.coef_
                    ).reshape(-1)
                )

        if fold_coefficients:

            mean_coefficients = np.mean(
                np.vstack(
                    fold_coefficients
                ),
                axis=0,
            )

            return {
                feature: float(coefficient)
                for feature, coefficient in zip(
                    features,
                    mean_coefficients,
                )
            }

    return {}


# ============================================================
# LOCAL CONTRIBUTIONS
# ============================================================

def _get_local_contributions(
    model,
    scaler,
    feature_row: Dict[str, Any],
    features: List[str],
) -> Dict[str, float]:
    """
    Calculate local Logistic Regression contributions.

    contribution =
        standardized_feature × coefficient

    Positive contribution:
        pushes toward higher risk.

    Negative contribution:
        pushes toward lower risk.

    These are model contributions, not causal claims.
    """

    coefficients = _get_logistic_coefficients(
        model,
        features,
    )

    if not coefficients:

        return {}

    # --------------------------------------------------------
    # Raw values
    # --------------------------------------------------------

    values = {}

    for feature in features:

        value = _numeric(
            feature_row.get(feature)
        )

        if value is None:

            value = 0.0

        values[feature] = value

    # --------------------------------------------------------
    # Preserve feature names
    # --------------------------------------------------------

    X = pd.DataFrame(
        [values],
        columns=features,
    )

    # --------------------------------------------------------
    # Apply exact production scaler
    # --------------------------------------------------------

    if scaler is not None:

        scaled_values = scaler.transform(
            X
        )[0]

    else:

        scaled_values = X.iloc[
            0
        ].to_numpy(
            dtype=float
        )

    # --------------------------------------------------------
    # Calculate raw contributions
    # --------------------------------------------------------

    contributions = {}

    for feature, scaled_value in zip(
        features,
        scaled_values,
    ):

        coefficient = coefficients.get(
            feature,
            0.0,
        )

        contributions[feature] = float(
            scaled_value
            * coefficient
        )

    return contributions


# ============================================================
# FUNCTION PROFILE
# ============================================================

def _build_function_profile(
    feature_row: Dict[str, Any],
    model,
    scaler,
    features: List[str],
):
    """
    Build an instance-specific profile.
    """

    contributions = _get_local_contributions(
        model=model,
        scaler=scaler,
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
            contributions.get(
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

    candidates.sort(
        key=lambda item: item[
            "absolute_contribution"
        ],
        reverse=True,
    )

    return candidates


# ============================================================
# NORMALIZE LOCAL IMPORTANCE
# ============================================================

def _normalize_local_importance(
    selected,
):
    """
    Convert local contribution magnitudes into relative
    importance values.

    The strongest feature gets 1.0.

    This is purely a UI representation.
    """

    if not selected:

        return selected

    total = sum(
        item["absolute_contribution"]
        for item in selected
    )

    if total <= 0:

        for item in selected:

            item["display_importance"] = 0.0

        return selected

    for item in selected:

        item["display_importance"] = (
            item["absolute_contribution"]
            / total
        )

    return selected


# ============================================================
# SIGNAL TEXT
# ============================================================

def _signal_text(
    feature: str,
    value: float,
    contribution: float,
) -> str:

    label = FEATURE_LABELS.get(
        feature,
        feature.replace(
            "_",
            " ",
        ),
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
# MAIN EXPLANATION FUNCTION
# ============================================================

def explain_prediction(
    feature_row: Dict[str, Any],
    feature_importances: Dict[str, float],
    risk_probability: float,
    model=None,
    features: List[str] = None,
    scaler=None,
) -> Dict[str, Any]:
    """
    Generate final CodeAtlas risk explanation.
    """

    probability = float(
        risk_probability
    )

    probability = max(
        0.0,
        min(
            probability,
            1.0,
        ),
    )

    # ========================================================
    # RISK LEVEL
    # ========================================================

    if probability < LOW_THRESHOLD:

        level = "Low"

    elif probability < HIGH_THRESHOLD:

        level = "Medium"

    else:

        level = "High"

    # ========================================================
    # FEATURES
    # ========================================================

    if features is None:

        features = list(
            feature_importances.keys()
        )

    # ========================================================
    # BUILD LOCAL PROFILE
    # ========================================================

    if model is not None:

        selected = _build_function_profile(
            feature_row=feature_row,
            model=model,
            scaler=scaler,
            features=features,
        )

    else:

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
    # Normalize local importance
    # --------------------------------------------------------

    selected = _normalize_local_importance(
        selected
    )

    # ========================================================
    # TOP FEATURES
    # ========================================================

    top_features = []

    for item in selected[:5]:

        feature = item[
            "feature"
        ]

        contribution = item[
            "contribution"
        ]

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

                "value": item[
                    "value"
                ],

                # Relative 0-1 local importance
                "importance": round(
                    item[
                        "display_importance"
                    ],
                    4,
                ),

                # Same normalized value for clean frontend use
                "contribution": round(
                    (
                        item[
                            "display_importance"
                        ]
                        if contribution >= 0
                        else -item[
                            "display_importance"
                        ]
                    ),
                    4,
                ),

                "direction": (
                    "increases risk"
                    if contribution > 0
                    else "reduces risk"
                ),
            }
        )

    # ========================================================
    # RISK-DRIVING SIGNALS
    # ========================================================

    reasons = []

    positive_features = [
        item
        for item in selected
        if item[
            "contribution"
        ] > 0
    ]

    positive_features.sort(
        key=lambda item: item[
            "contribution"
        ],
        reverse=True,
    )

    for item in positive_features[:3]:

        reasons.append(
            _signal_text(
                feature=item[
                    "feature"
                ],
                value=item[
                    "value"
                ],
                contribution=item[
                    "contribution"
                ],
            )
        )

    # ========================================================
    # FALLBACK
    # ========================================================

    if not reasons:

        if selected:

            strongest = selected[0]

            label = FEATURE_LABELS.get(
                strongest[
                    "feature"
                ],
                strongest[
                    "feature"
                ].replace(
                    "_",
                    " ",
                ),
            )

            formatted = _format_value(
                strongest[
                    "feature"
                ],
                strongest[
                    "value"
                ],
            )

            reasons.append(
                "No major risk-driving signal "
                "detected; strongest local feature "
                f"was {label} ({formatted})."
            )

        else:

            reasons.append(
                "No strong risk-driving signals detected."
            )

    reasons = reasons[:3]

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "risk_level": level,

        "risk_probability": round(
            probability,
            4,
        ),

        "risk_index": round(
            probability * 100,
            2,
        ),

        "risk_score": round(
            probability * 100,
            2,
        ),

        "reasons": reasons,

        "top_features": top_features,
    }