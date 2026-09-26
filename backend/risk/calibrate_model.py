from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "bugsinpy_features_full.csv"
MODEL_DIR = BASE_DIR / "models"


def evaluate_probabilities(name, y_true, probabilities):
    brier = brier_score_loss(y_true, probabilities)
    logloss = log_loss(y_true, probabilities)
    roc_auc = roc_auc_score(y_true, probabilities)
    pr_auc = average_precision_score(y_true, probabilities)

    print(
        f"{name:<22}"
        f"Brier: {brier:.4f} | "
        f"LogLoss: {logloss:.4f} | "
        f"ROC-AUC: {roc_auc:.4f} | "
        f"PR-AUC: {pr_auc:.4f}"
    )

    return {
        "model": name,
        "brier": brier,
        "log_loss": logloss,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
    }


def main():
    print("=" * 80)
    print("CODEATLAS - PROJECT-AWARE PROBABILITY CALIBRATION")
    print("=" * 80)

    df = pd.read_csv(DATA_PATH)

    features = joblib.load(MODEL_DIR / "features.pkl")

    X = df[features].copy()
    y = df["label"].astype(int)
    groups = df["repository"]

    logo = LeaveOneGroupOut()

    # OOF probabilities
    raw_oof = np.zeros(len(df))
    sigmoid_oof = np.zeros(len(df))
    isotonic_oof = np.zeros(len(df))

    print(f"\nSamples:  {len(df)}")
    print(f"Projects: {groups.nunique()}")

    print("\nGenerating calibrated OOF probabilities...\n")

    for fold, (train_idx, test_idx) in enumerate(
        logo.split(X, y, groups),
        start=1,
    ):
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]

        y_train = y.iloc[train_idx]

        test_project = groups.iloc[test_idx].iloc[0]

        # ---------------------------------------------------------
        # Scale using TRAINING PROJECTS ONLY
        # ---------------------------------------------------------
        scaler = StandardScaler()

        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # ---------------------------------------------------------
        # Base logistic model
        # ---------------------------------------------------------
        base_model = LogisticRegression(
            max_iter=5000,
            class_weight="balanced",
            random_state=42,
        )

        # ---------------------------------------------------------
        # Raw model
        # ---------------------------------------------------------
        base_model.fit(
            X_train_scaled,
            y_train,
        )

        raw_probabilities = base_model.predict_proba(
            X_test_scaled
        )[:, 1]

        raw_oof[test_idx] = raw_probabilities

        # ---------------------------------------------------------
        # Sigmoid calibration
        #
        # Calibration data comes ONLY from the training projects.
        # ---------------------------------------------------------
        sigmoid_model = CalibratedClassifierCV(
            estimator=LogisticRegression(
                max_iter=5000,
                class_weight="balanced",
                random_state=42,
            ),
            method="sigmoid",
            cv=5,
        )

        sigmoid_model.fit(
            X_train_scaled,
            y_train,
        )

        sigmoid_probabilities = sigmoid_model.predict_proba(
            X_test_scaled
        )[:, 1]

        sigmoid_oof[test_idx] = sigmoid_probabilities

        # ---------------------------------------------------------
        # Isotonic calibration
        # ---------------------------------------------------------
        isotonic_model = CalibratedClassifierCV(
            estimator=LogisticRegression(
                max_iter=5000,
                class_weight="balanced",
                random_state=42,
            ),
            method="isotonic",
            cv=5,
        )

        isotonic_model.fit(
            X_train_scaled,
            y_train,
        )

        isotonic_probabilities = isotonic_model.predict_proba(
            X_test_scaled
        )[:, 1]

        isotonic_oof[test_idx] = isotonic_probabilities

        print(
            f"Fold {fold:2d} | "
            f"Test project: {test_project:15s} | "
            f"Samples: {len(test_idx):4d}"
        )

    # ---------------------------------------------------------
    # Evaluate
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("CALIBRATION RESULTS")
    print("=" * 80)

    results = []

    results.append(
        evaluate_probabilities(
            "Raw Logistic",
            y,
            raw_oof,
        )
    )

    results.append(
        evaluate_probabilities(
            "Sigmoid",
            y,
            sigmoid_oof,
        )
    )

    results.append(
        evaluate_probabilities(
            "Isotonic",
            y,
            isotonic_oof,
        )
    )

    results_df = pd.DataFrame(results)

    output_path = MODEL_DIR / "calibration_results.csv"

    results_df.to_csv(
        output_path,
        index=False,
    )

    # ---------------------------------------------------------
    # Save all OOF probabilities
    # ---------------------------------------------------------
    probability_df = df[
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

    probability_df["raw_probability"] = raw_oof
    probability_df["sigmoid_probability"] = sigmoid_oof
    probability_df["isotonic_probability"] = isotonic_oof

    probability_path = (
        MODEL_DIR / "calibrated_oof_predictions.csv"
    )

    probability_df.to_csv(
        probability_path,
        index=False,
    )

    # ---------------------------------------------------------
    # Select calibration method
    # Lowest Brier score is better.
    # ---------------------------------------------------------
    best = results_df.loc[
        results_df["brier"].idxmin()
    ]

    print("\n" + "=" * 80)
    print("BEST CALIBRATION METHOD")
    print("=" * 80)

    print(f"Method:   {best['model']}")
    print(f"Brier:    {best['brier']:.4f}")
    print(f"LogLoss:  {best['log_loss']:.4f}")
    print(f"ROC-AUC:  {best['roc_auc']:.4f}")
    print(f"PR-AUC:   {best['pr_auc']:.4f}")

    print("\nSaved:")
    print(output_path)
    print(probability_path)


if __name__ == "__main__":
    main()