from pathlib import Path

import joblib
import pandas as pd

from backend.risk.explainer import (
    explain_prediction,
    get_feature_importances,
)


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "random_forest.pkl"
FEATURES_PATH = MODEL_DIR / "features.pkl"


class RiskPredictor:

    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        self.features = joblib.load(FEATURES_PATH)

        self.feature_importances = get_feature_importances(
            self.model,
            self.features,
        )

    def predict(self, feature_rows):

        if not feature_rows:
            return []

        df = pd.DataFrame(feature_rows)

        X = df[self.features]

        probabilities = self.model.predict_proba(X)[:, 1]

        predictions = []

        for row, probability in zip(
            feature_rows,
            probabilities,
        ):

            probability = float(probability)

            explanation = explain_prediction(
                feature_row=row,
                feature_importances=self.feature_importances,
                risk_probability=probability,
            )

            predictions.append(
                {
                    "id": row["id"],
                    "file": row["file"],
                    "function": row["function"],
                    **explanation,
                }
            )

        return predictions