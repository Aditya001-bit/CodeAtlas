from pathlib import Path

import joblib
import pandas as pd

from backend.risk.explainer import (
    explain_prediction,
    get_feature_importances,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "random_forest.pkl"
FEATURES_PATH = MODEL_DIR / "features.pkl"


# ============================================================
# RISK PREDICTOR
# ============================================================

class RiskPredictor:

    def __init__(self):

        # ----------------------------------------------------
        # Load trained Random Forest
        # ----------------------------------------------------

        self.model = joblib.load(
            MODEL_PATH
        )

        # ----------------------------------------------------
        # Load exact feature order used during training
        # ----------------------------------------------------

        self.features = joblib.load(
            FEATURES_PATH
        )

        # ----------------------------------------------------
        # Global feature importance
        #
        # Used only as model metadata.
        # SHAP handles individual explanations.
        # ----------------------------------------------------

        self.feature_importances = (
            get_feature_importances(
                self.model,
                self.features,
            )
        )

    # ========================================================
    # PREDICT
    # ========================================================

    def predict(
        self,
        feature_rows,
    ):

        if not feature_rows:
            return []

        # ----------------------------------------------------
        # Convert feature rows to DataFrame
        # ----------------------------------------------------

        df = pd.DataFrame(
            feature_rows
        )

        # ----------------------------------------------------
        # Select the exact features used during training
        # ----------------------------------------------------

        X = df[
            self.features
        ]

        # ----------------------------------------------------
        # Random Forest prediction
        #
        # Class 1 = risky
        # ----------------------------------------------------

        probabilities = (
            self.model
            .predict_proba(X)[:, 1]
        )

        predictions = []

        # ====================================================
        # Explain EACH function individually
        # ====================================================

        for row, probability in zip(
            feature_rows,
            probabilities,
        ):

            probability = float(
                probability
            )

            # ------------------------------------------------
            # SHAP explanation
            #
            # IMPORTANT:
            # Pass the actual trained model and feature list.
            # This allows explainer.py to calculate LOCAL
            # feature contributions for this function.
            # ------------------------------------------------

            explanation = explain_prediction(
                feature_row=row,

                feature_importances=(
                    self.feature_importances
                ),

                risk_probability=(
                    probability
                ),

                model=self.model,

                features=self.features,
            )

            # ------------------------------------------------
            # Build final response
            # ------------------------------------------------

            predictions.append(
                {
                    "id": row["id"],
                    "file": row["file"],
                    "function": row.get(
                        "function",
                        row.get(
                            "name",
                            "Module",
                        ),
                    ),

                    **explanation,
                }
            )

        return predictions