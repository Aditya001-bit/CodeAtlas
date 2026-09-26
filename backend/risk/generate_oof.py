from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "bugsinpy_features_full.csv"
MODEL_DIR = BASE_DIR / "models"

OUTPUT_PATH = MODEL_DIR / "logistic_oof_predictions.csv"


def main():
    print("=" * 70)
    print("CODEATLAS - LEAKAGE-SAFE OOF PREDICTIONS")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Load dataset
    # ---------------------------------------------------------
    df = pd.read_csv(DATA_PATH)

    print(f"\nDataset shape: {df.shape}")
    print(f"Projects: {df['repository'].nunique()}")
    print(f"Positive samples: {(df['label'] == 1).sum()}")
    print(f"Negative samples: {(df['label'] == 0).sum()}")

    # ---------------------------------------------------------
    # 2. Load the exact feature list used by training
    # ---------------------------------------------------------
    features = joblib.load(MODEL_DIR / "features.pkl")

    print("\nFeatures:")
    for feature in features:
        print(f"  - {feature}")

    X = df[features].copy()
    y = df["label"].astype(int)
    groups = df["repository"]

    # ---------------------------------------------------------
    # 3. Leave-One-Project-Out CV
    # ---------------------------------------------------------
    logo = LeaveOneGroupOut()

    oof_probability = np.zeros(len(df), dtype=float)

    print("\nGenerating out-of-fold predictions...")

    for fold, (train_idx, test_idx) in enumerate(
        logo.split(X, y, groups),
        start=1,
    ):
        train_projects = groups.iloc[train_idx].unique()
        test_project = groups.iloc[test_idx].iloc[0]

        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]

        y_train = y.iloc[train_idx]

        # -----------------------------------------------------
        # Fit scaler ONLY on training projects
        # -----------------------------------------------------
        scaler = StandardScaler()

        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # -----------------------------------------------------
        # Fresh Logistic Regression for this fold
        # -----------------------------------------------------
        model = LogisticRegression(
            max_iter=5000,
            class_weight="balanced",
            random_state=42,
        )

        model.fit(X_train_scaled, y_train)

        probabilities = model.predict_proba(X_test_scaled)[:, 1]

        oof_probability[test_idx] = probabilities

        print(
            f"Fold {fold:2d} | "
            f"Train projects: {len(train_projects):2d} | "
            f"Test: {test_project:15s} | "
            f"Samples: {len(test_idx):4d}"
        )

    # ---------------------------------------------------------
    # 4. Store predictions
    # ---------------------------------------------------------
    result = df[
        [
            "sample_id",
            "repository",
            "bug_id",
            "commit",
            "id",
            "file",
            "function",
            "label",
        ]
    ].copy()

    result["probability"] = oof_probability

    result.to_csv(OUTPUT_PATH, index=False)

    # ---------------------------------------------------------
    # 5. Overall OOF performance at default threshold = 0.5
    # ---------------------------------------------------------
    predictions = (oof_probability >= 0.5).astype(int)

    print("\n" + "=" * 70)
    print("OOF PERFORMANCE @ THRESHOLD 0.50")
    print("=" * 70)

    print(f"ROC-AUC:           {roc_auc_score(y, oof_probability):.4f}")
    print(f"PR-AUC:            {average_precision_score(y, oof_probability):.4f}")
    print(f"Balanced Accuracy: {balanced_accuracy_score(y, predictions):.4f}")
    print(f"Precision:         {precision_score(y, predictions, zero_division=0):.4f}")
    print(f"Recall:            {recall_score(y, predictions, zero_division=0):.4f}")
    print(f"F1:                {f1_score(y, predictions, zero_division=0):.4f}")

    print("\nSaved:")
    print(OUTPUT_PATH)

    print("\n" + "=" * 70)
    print("OOF GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()