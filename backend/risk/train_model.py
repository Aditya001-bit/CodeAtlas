from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler

from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET = BASE_DIR / "data" / "bugsinpy_features_full.csv"

MODEL_DIR = BASE_DIR / "models"

MODEL_DIR.mkdir(exist_ok=True)


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_STATE = 42

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


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(y_true, y_pred, y_prob):

    return {
        "accuracy": accuracy_score(
            y_true,
            y_pred,
        ),

        "balanced_accuracy": balanced_accuracy_score(
            y_true,
            y_pred,
        ),

        "precision": precision_score(
            y_true,
            y_pred,
            zero_division=0,
        ),

        "recall": recall_score(
            y_true,
            y_pred,
            zero_division=0,
        ),

        "f1": f1_score(
            y_true,
            y_pred,
            zero_division=0,
        ),

        "roc_auc": roc_auc_score(
            y_true,
            y_prob,
        ),

        "pr_auc": average_precision_score(
            y_true,
            y_prob,
        ),
    }


# ============================================================
# MODEL BUILDERS
# ============================================================

def build_models():

    return {

        "Dummy Baseline": DummyClassifier(
            strategy="prior",
            random_state=RANDOM_STATE,
        ),

        "Logistic Regression": LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),

        "Random Forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_split=4,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),

        "XGBoost": XGBClassifier(
            n_estimators=500,
            max_depth=5,
            learning_rate=0.03,
            min_child_weight=2,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


# ============================================================
# PROJECT-AWARE CROSS VALIDATION
# ============================================================

def evaluate_project_aware(
    X,
    y,
    groups,
    features,
):

    logo = LeaveOneGroupOut()

    models = build_models()

    results = {
        name: {
            "y_true": [],
            "y_pred": [],
            "y_prob": [],
        }
        for name in models
    }

    fold_rows = []

    print()
    print("=" * 70)
    print("PROJECT-AWARE CROSS-VALIDATION")
    print("=" * 70)

    for fold, (train_idx, test_idx) in enumerate(
        logo.split(
            X,
            y,
            groups,
        ),
        start=1,
    ):

        test_project = groups.iloc[
            test_idx
        ].iloc[0]

        X_train = X.iloc[
            train_idx
        ]

        X_test = X.iloc[
            test_idx
        ]

        y_train = y.iloc[
            train_idx
        ]

        y_test = y.iloc[
            test_idx
        ]

        print()
        print(
            f"Fold {fold:02d} | "
            f"Test project: {test_project} | "
            f"Train: {len(train_idx)} | "
            f"Test: {len(test_idx)}"
        )

        # ----------------------------------------------------
        # Scale only Logistic Regression.
        # ----------------------------------------------------

        scaler = StandardScaler()

        X_train_scaled = scaler.fit_transform(
            X_train
        )

        X_test_scaled = scaler.transform(
            X_test
        )

        for name, model in models.items():

            if name == "Logistic Regression":

                model.fit(
                    X_train_scaled,
                    y_train,
                )

                predictions = model.predict(
                    X_test_scaled
                )

                probabilities = model.predict_proba(
                    X_test_scaled
                )[:, 1]

            else:

                model.fit(
                    X_train,
                    y_train,
                )

                predictions = model.predict(
                    X_test
                )

                probabilities = model.predict_proba(
                    X_test
                )[:, 1]

            results[name]["y_true"].extend(
                y_test.tolist()
            )

            results[name]["y_pred"].extend(
                predictions.tolist()
            )

            results[name]["y_prob"].extend(
                probabilities.tolist()
            )

            metrics = calculate_metrics(
                y_test,
                predictions,
                probabilities,
            )

            fold_rows.append(
                {
                    "fold": fold,
                    "test_project": test_project,
                    "model": name,
                    **metrics,
                }
            )

            print(
                f"    {name:<22}"
                f" F1={metrics['f1']:.3f}"
                f" | PR-AUC={metrics['pr_auc']:.3f}"
            )

    return results, pd.DataFrame(
        fold_rows
    )


# ============================================================
# FINAL CROSS-PROJECT RESULTS
# ============================================================

def print_final_results(results):

    summary = []

    print()
    print("=" * 70)
    print("FINAL PROJECT-AWARE RESULTS")
    print("=" * 70)

    for name, result in results.items():

        y_true = np.array(
            result["y_true"]
        )

        y_pred = np.array(
            result["y_pred"]
        )

        y_prob = np.array(
            result["y_prob"]
        )

        metrics = calculate_metrics(
            y_true,
            y_pred,
            y_prob,
        )

        summary.append(
            {
                "model": name,
                **metrics,
            }
        )

        print()
        print(name)
        print("-" * 50)

        print(
            f"Accuracy          : "
            f"{metrics['accuracy']:.4f}"
        )

        print(
            f"Balanced Accuracy : "
            f"{metrics['balanced_accuracy']:.4f}"
        )

        print(
            f"Precision         : "
            f"{metrics['precision']:.4f}"
        )

        print(
            f"Recall            : "
            f"{metrics['recall']:.4f}"
        )

        print(
            f"F1                : "
            f"{metrics['f1']:.4f}"
        )

        print(
            f"ROC-AUC           : "
            f"{metrics['roc_auc']:.4f}"
        )

        print(
            f"PR-AUC            : "
            f"{metrics['pr_auc']:.4f}"
        )

        print()
        print("Confusion Matrix:")

        print(
            confusion_matrix(
                y_true,
                y_pred,
            )
        )

    return pd.DataFrame(
        summary
    )


# ============================================================
# TRAIN FINAL MODELS ON ALL DATA
# ============================================================

def train_final_models(
    X,
    y,
):

    print()
    print("=" * 70)
    print("TRAINING FINAL MODELS ON ALL DATA")
    print("=" * 70)

    models = build_models()

    # --------------------------------------------------------
    # Logistic Regression
    # --------------------------------------------------------

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        X
    )

    logistic = models[
        "Logistic Regression"
    ]

    print(
        "Training final Logistic Regression..."
    )

    logistic.fit(
        X_scaled,
        y,
    )

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    random_forest = models[
        "Random Forest"
    ]

    print(
        "Training final Random Forest..."
    )

    random_forest.fit(
        X,
        y,
    )

    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    xgboost = models[
        "XGBoost"
    ]

    print(
        "Training final XGBoost..."
    )

    xgboost.fit(
        X,
        y,
    )

    return {
        "logistic": logistic,
        "random_forest": random_forest,
        "xgboost": xgboost,
        "scaler": scaler,
    }


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(
    random_forest,
    xgboost,
    features,
):

    rf_importance = pd.DataFrame(
        {
            "feature": features,
            "importance":
                random_forest.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    xgb_importance = pd.DataFrame(
        {
            "feature": features,
            "importance":
                xgboost.feature_importances_,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    rf_importance.to_csv(
        MODEL_DIR /
        "rf_feature_importance.csv",
        index=False,
    )

    xgb_importance.to_csv(
        MODEL_DIR /
        "xgb_feature_importance.csv",
        index=False,
    )

    print()
    print("=" * 70)
    print("RANDOM FOREST FEATURE IMPORTANCE")
    print("=" * 70)

    print(
        rf_importance.to_string(
            index=False
        )
    )

    print()
    print("=" * 70)
    print("XGBOOST FEATURE IMPORTANCE")
    print("=" * 70)

    print(
        xgb_importance.to_string(
            index=False
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("CODEATLAS FINAL ML TRAINING PIPELINE")
    print("=" * 70)

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    print()
    print("Loading dataset...")

    if not DATASET.exists():

        raise FileNotFoundError(
            f"Dataset not found: {DATASET}"
        )

    df = pd.read_csv(
        DATASET
    )

    print(
        f"Dataset: {DATASET}"
    )

    print(
        f"Total samples: {len(df)}"
    )

    print(
        f"Positive samples: "
        f"{(df['label'] == 1).sum()}"
    )

    print(
        f"Negative samples: "
        f"{(df['label'] == 0).sum()}"
    )

    print(
        f"Projects: "
        f"{df['repository'].nunique()}"
    )

    # --------------------------------------------------------
    # Remove constant features
    # --------------------------------------------------------

    constant_features = [
        feature
        for feature in FEATURES
        if df[feature].nunique() <= 1
    ]

    final_features = [
        feature
        for feature in FEATURES
        if feature not in constant_features
    ]

    print()

    if constant_features:

        print(
            "Removed constant features:"
        )

        for feature in constant_features:

            print(
                f"  - {feature}"
            )

    print()
    print(
        f"Final ML features: "
        f"{len(final_features)}"
    )

    print(
        final_features
    )

    # --------------------------------------------------------
    # Prepare X, y, groups
    # --------------------------------------------------------

    X = df[
        final_features
    ].copy()

    y = df[
        "label"
    ].astype(int)

    groups = df[
        "repository"
    ].astype(str)

    # --------------------------------------------------------
    # PROJECT-AWARE VALIDATION
    # --------------------------------------------------------

    results, fold_results = (
        evaluate_project_aware(
            X,
            y,
            groups,
            final_features,
        )
    )

    # --------------------------------------------------------
    # FINAL RESULTS
    # --------------------------------------------------------

    summary = print_final_results(
        results
    )

    # --------------------------------------------------------
    # Save validation results
    # --------------------------------------------------------

    summary.to_csv(
        MODEL_DIR /
        "cross_project_results.csv",
        index=False,
    )

    fold_results.to_csv(
        MODEL_DIR /
        "cross_project_folds.csv",
        index=False,
    )

    # --------------------------------------------------------
    # Select model using PR-AUC first,
    # then F1 as tie-breaker.
    # --------------------------------------------------------

    ranked = summary.sort_values(
        by=[
            "pr_auc",
            "f1",
        ],
        ascending=False,
    )

    selected_model = ranked.iloc[
        0
    ]["model"]

    # --------------------------------------------------------
    # Do not allow Dummy to become
    # the production model.
    # --------------------------------------------------------

    if selected_model == "Dummy Baseline":

        candidates = summary[
            summary["model"] !=
            "Dummy Baseline"
        ].sort_values(
            by=[
                "pr_auc",
                "f1",
            ],
            ascending=False,
        )

        selected_model = candidates.iloc[
            0
        ]["model"]

    print()
    print("=" * 70)
    print("MODEL SELECTION")
    print("=" * 70)

    print(
        f"Selected model: "
        f"{selected_model}"
    )

    # --------------------------------------------------------
    # Train final models on ALL samples.
    # --------------------------------------------------------

    final_models = train_final_models(
        X,
        y,
    )

    # --------------------------------------------------------
    # Save models.
    # --------------------------------------------------------

    joblib.dump(
        final_models["random_forest"],
        MODEL_DIR /
        "random_forest.pkl",
    )

    joblib.dump(
        final_models["xgboost"],
        MODEL_DIR /
        "xgboost.pkl",
    )

    joblib.dump(
        final_models["logistic"],
        MODEL_DIR /
        "logistic_regression.pkl",
    )

    joblib.dump(
        final_models["scaler"],
        MODEL_DIR /
        "scaler.pkl",
    )

    joblib.dump(
        final_features,
        MODEL_DIR /
        "features.pkl",
    )

    joblib.dump(
        selected_model,
        MODEL_DIR /
        "selected_model.pkl",
    )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    save_feature_importance(
        final_models["random_forest"],
        final_models["xgboost"],
        final_features,
    )

    # --------------------------------------------------------
    # Training metadata
    # --------------------------------------------------------

    metadata = {
        "dataset": str(DATASET),
        "samples": int(len(df)),
        "positive_samples": int(
            (y == 1).sum()
        ),
        "negative_samples": int(
            (y == 0).sum()
        ),
        "projects": int(
            groups.nunique()
        ),
        "features": final_features,
        "removed_constant_features":
            constant_features,
        "validation":
            "Leave-One-Project-Out",
        "selection_metric":
            "PR-AUC",
        "selected_model":
            selected_model,
        "random_state":
            RANDOM_STATE,
    }

    joblib.dump(
        metadata,
        MODEL_DIR /
        "training_metadata.pkl",
    )

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)

    print()
    print(
        f"Final dataset: "
        f"{len(df)} samples"
    )

    print(
        f"Final features: "
        f"{len(final_features)}"
    )

    print(
        f"Selected model: "
        f"{selected_model}"
    )

    print()
    print(
        "Models saved to:"
    )

    print(
        MODEL_DIR
    )

    print()
    print(
        "Validation results:"
    )

    print(
        MODEL_DIR /
        "cross_project_results.csv"
    )


if __name__ == "__main__":
    main()