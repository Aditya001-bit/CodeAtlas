from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


BASE_DIR = Path(__file__).resolve().parent
DATASET = BASE_DIR / "data" / "bugsinpy_features.csv"
MODEL_DIR = BASE_DIR / "models"

MODEL_DIR.mkdir(exist_ok=True)


FEATURES = [
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
    "betweenness",
    "pagerank",
]


def evaluate_model(name, model, X_test, y_test):
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    auc = roc_auc_score(y_test, probabilities)

    print()
    print("=" * 50)
    print(name)
    print("=" * 50)

    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {auc:.4f}")

    print()
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    print()
    print("Classification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc,
    }


def main():
    print("Loading dataset...")

    df = pd.read_csv(DATASET)

    print(f"Total samples: {len(df)}")
    print(f"Positive samples: {(df['label'] == 1).sum()}")
    print(f"Negative samples: {(df['label'] == 0).sum()}")

    X = df[FEATURES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    print()
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples:  {len(X_test)}")

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    print()
    print("Training Random Forest...")
    rf.fit(X_train, y_train)

    print("Training XGBoost...")
    xgb.fit(X_train, y_train)

    rf_results = evaluate_model(
        "Random Forest",
        rf,
        X_test,
        y_test,
    )

    xgb_results = evaluate_model(
        "XGBoost",
        xgb,
        X_test,
        y_test,
    )

    joblib.dump(
        rf,
        MODEL_DIR / "random_forest.pkl",
    )

    joblib.dump(
        xgb,
        MODEL_DIR / "xgboost.pkl",
    )

    joblib.dump(
        scaler,
        MODEL_DIR / "scaler.pkl",
    )

    joblib.dump(
        FEATURES,
        MODEL_DIR / "features.pkl",
    )

    print()
    print("=" * 50)
    print("MODEL COMPARISON")
    print("=" * 50)

    print(
        f"Random Forest | "
        f"Accuracy: {rf_results['accuracy']:.4f} | "
        f"F1: {rf_results['f1']:.4f} | "
        f"ROC-AUC: {rf_results['roc_auc']:.4f}"
    )

    print(
        f"XGBoost       | "
        f"Accuracy: {xgb_results['accuracy']:.4f} | "
        f"F1: {xgb_results['f1']:.4f} | "
        f"ROC-AUC: {xgb_results['roc_auc']:.4f}"
    )

    print()
    print("Models saved to:")
    print(MODEL_DIR)


if __name__ == "__main__":
    main()