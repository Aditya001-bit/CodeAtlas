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

MODEL_PATH = MODEL_DIR / "codeatlas_risk_model.pkl"


# ============================================================
# RISK PREDICTOR
# ============================================================

class RiskPredictor:

    def __init__(self):

        # ----------------------------------------------------
        # Load final production artifact
        # ----------------------------------------------------

        artifact = joblib.load(
            MODEL_PATH
        )

        # ----------------------------------------------------
        # Extract production components
        # ----------------------------------------------------

        self.model = artifact["model"]

        self.scaler = artifact["scaler"]

        self.features = artifact["features"]

        # ----------------------------------------------------
        # Final risk configuration
        # ----------------------------------------------------

        self.classification_threshold = float(
            artifact["classification_threshold"]
        )

        self.low_threshold = float(
            artifact["low_threshold"]
        )

        self.high_threshold = float(
            artifact["high_threshold"]
        )

        self.calibration_method = (
            artifact["calibration_method"]
        )

        self.model_type = (
            artifact["model_type"]
        )

        # ----------------------------------------------------
        # Global feature importance
        # ----------------------------------------------------

        self.feature_importances = (
            get_feature_importances(
                self.model,
                self.features,
            )
        )

    # ========================================================
    # RISK LEVEL
    # ========================================================

    def _get_risk_level(
        self,
        probability,
    ):

        if probability < self.low_threshold:

            return "Low"

        elif probability < self.high_threshold:

            return "Medium"

        else:

            return "High"

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
        # Select exact training features
        # ----------------------------------------------------

        X = df[
            self.features
        ]

        # ----------------------------------------------------
        # Apply exact production scaler
        # ----------------------------------------------------

        X_scaled = (
            self.scaler.transform(
                X
            )
        )

        # ----------------------------------------------------
        # Get calibrated probability
        #
        # Class 1 = risky.
        # ----------------------------------------------------

        probabilities = (
            self.model
            .predict_proba(
                X_scaled
            )[:, 1]
        )

        predictions = []

        # ====================================================
        # Explain EACH function
        # ====================================================

        for row, probability in zip(
            feature_rows,
            probabilities,
        ):

            probability = float(
                probability
            )

            # ------------------------------------------------
            # Risk Index
            # ------------------------------------------------

            risk_index = round(
                probability * 100,
                2,
            )

            # ------------------------------------------------
            # Risk Level
            # ------------------------------------------------

            risk_level = (
                self._get_risk_level(
                    probability
                )
            )

            # ------------------------------------------------
            # Instance-specific explanation
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

                scaler=self.scaler,
            )

            # ------------------------------------------------
            # Final response
            # ------------------------------------------------

            prediction = {
                "id": row["id"],

                "file": row["file"],

                "function": row.get(
                    "function",
                    row.get(
                        "name",
                        "Module",
                    ),
                ),

                "risk_probability": round(
                    probability,
                    4,
                ),

                "risk_index": risk_index,

                "risk_level": risk_level,

                # Backward compatibility
                "risk_score": risk_index,

                **explanation,
            }

            # ------------------------------------------------
            # Always enforce production ML values
            # ------------------------------------------------

            prediction["risk_probability"] = round(
                probability,
                4,
            )

            prediction["risk_index"] = (
                risk_index
            )

            prediction["risk_score"] = (
                risk_index
            )

            prediction["risk_level"] = (
                risk_level
            )

            predictions.append(
                prediction
            )

        return predictions