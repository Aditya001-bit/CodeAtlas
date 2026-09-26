from pathlib import Path

import joblib
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "data" / "bugsinpy_features_full.csv"
MODEL_DIR = BASE_DIR / "models"

OUTPUT_PATH = MODEL_DIR / "codeatlas_risk_model.pkl"


# ---------------------------------------------------------
# CodeAtlas production configuration
# ---------------------------------------------------------

CLASSIFICATION_THRESHOLD = 0.30

LOW_THRESHOLD = 0.20
HIGH_THRESHOLD = 0.30

CALIBRATION_METHOD = "isotonic"


def main():
    print("=" * 80)
    print("CODEATLAS - FINAL PRODUCTION RISK MODEL")
    print("=" * 80)

    # -----------------------------------------------------
    # 1. Load complete dataset
    # -----------------------------------------------------

    df = pd.read_csv(DATA_PATH)

    print("\nDataset")
    print("-" * 80)

    print(f"Samples:          {len(df)}")
    print(f"Projects:         {df['repository'].nunique()}")
    print(f"Positive samples: {(df['label'] == 1).sum()}")
    print(f"Negative samples: {(df['label'] == 0).sum()}")

    # -----------------------------------------------------
    # 2. Load exact features selected during training
    # -----------------------------------------------------

    features = joblib.load(
        MODEL_DIR / "features.pkl"
    )

    print("\nFeatures")
    print("-" * 80)

    for feature in features:
        print(f"  {feature}")

    X = df[features].copy()
    y = df["label"].astype(int)

    # -----------------------------------------------------
    # 3. Fit scaler on COMPLETE training dataset
    # -----------------------------------------------------

    print("\nFitting StandardScaler...")

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    # -----------------------------------------------------
    # 4. Base Logistic Regression
    # -----------------------------------------------------

    print("Building Logistic Regression...")

    base_model = LogisticRegression(
        max_iter=5000,
        class_weight="balanced",
        random_state=42,
    )

    # -----------------------------------------------------
    # 5. Isotonic calibration
    #
    # The calibrated classifier internally performs
    # cross-validation on the complete training dataset.
    # -----------------------------------------------------

    print("Applying isotonic probability calibration...")

    calibrated_model = CalibratedClassifierCV(
        estimator=base_model,
        method=CALIBRATION_METHOD,
        cv=5,
    )

    calibrated_model.fit(
        X_scaled,
        y,
    )

    # -----------------------------------------------------
    # 6. Create a single deployment artifact
    # -----------------------------------------------------

    artifact = {
        "model": calibrated_model,
        "scaler": scaler,
        "features": features,

        # Classification threshold selected from
        # leakage-safe project-aware OOF analysis.
        "classification_threshold": CLASSIFICATION_THRESHOLD,

        # Risk-band boundaries.
        "low_threshold": LOW_THRESHOLD,
        "high_threshold": HIGH_THRESHOLD,

        "calibration_method": CALIBRATION_METHOD,

        # Dataset metadata.
        "training_samples": len(df),
        "training_projects": int(df["repository"].nunique()),
        "positive_samples": int((df["label"] == 1).sum()),
        "negative_samples": int((df["label"] == 0).sum()),

        # Version information.
        "model_type": "LogisticRegression + IsotonicCalibration",
        "version": "codeatlas-risk-v2",
    }

    joblib.dump(
        artifact,
        OUTPUT_PATH,
    )

    # -----------------------------------------------------
    # 7. Verify artifact
    # -----------------------------------------------------

    print("\nVerifying saved artifact...")

    loaded = joblib.load(
        OUTPUT_PATH
    )

    print(
        f"Model type:        {loaded['model_type']}"
    )

    print(
        f"Calibration:       {loaded['calibration_method']}"
    )

    print(
        f"Features:          {len(loaded['features'])}"
    )

    print(
        f"Training samples:  {loaded['training_samples']}"
    )

    print(
        f"Projects:          {loaded['training_projects']}"
    )

    print(
        f"Risk threshold:    {loaded['classification_threshold']}"
    )

    print(
        f"LOW threshold:     {loaded['low_threshold']}"
    )

    print(
        f"HIGH threshold:    {loaded['high_threshold']}"
    )

    # -----------------------------------------------------
    # 8. Test predictions
    # -----------------------------------------------------

    probabilities = calibrated_model.predict_proba(
        X_scaled
    )[:, 1]

    print("\nTraining-data prediction sanity check")
    print("-" * 80)

    print(
        f"Minimum probability: {probabilities.min():.4f}"
    )

    print(
        f"Maximum probability: {probabilities.max():.4f}"
    )

    print(
        f"Mean probability:    {probabilities.mean():.4f}"
    )

    print(
        f"Median probability:  {pd.Series(probabilities).median():.4f}"
    )

    # -----------------------------------------------------
    # 9. Risk distribution
    # -----------------------------------------------------

    risk_levels = []

    for probability in probabilities:

        if probability < LOW_THRESHOLD:
            risk_levels.append("Low")

        elif probability < HIGH_THRESHOLD:
            risk_levels.append("Medium")

        else:
            risk_levels.append("High")

    risk_series = pd.Series(risk_levels)

    print("\nRisk distribution")
    print("-" * 80)

    print(
        risk_series.value_counts()
        .reindex(
            ["Low", "Medium", "High"],
            fill_value=0,
        )
        .to_string()
    )

    # -----------------------------------------------------
    # 10. Final output
    # -----------------------------------------------------

    print("\n" + "=" * 80)
    print("FINAL MODEL CREATED")
    print("=" * 80)

    print(f"\nSaved to:")

    print(
        OUTPUT_PATH
    )

    print("\nProduction pipeline:")

    print(
        "Features -> StandardScaler -> "
        "Logistic Regression -> Isotonic Calibration"
    )

    print("\nRisk configuration:")

    print(
        "LOW:     probability < 0.20"
    )

    print(
        "MEDIUM:  0.20 <= probability < 0.30"
    )

    print(
        "HIGH:    probability >= 0.30"
    )

    print("\nRisk Index:")

    print(
        "Risk Index = calibrated_probability * 100"
    )


if __name__ == "__main__":
    main()