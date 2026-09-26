from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
)


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "models" / "logistic_oof_predictions.csv"


def main():
    df = pd.read_csv(INPUT_PATH)

    y_true = df["label"]
    probabilities = df["probability"]

    thresholds = [
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
        0.80,
    ]

    results = []

    for threshold in thresholds:
        predictions = (probabilities >= threshold).astype(int)

        precision = precision_score(
            y_true,
            predictions,
            zero_division=0,
        )

        recall = recall_score(
            y_true,
            predictions,
            zero_division=0,
        )

        f1 = f1_score(
            y_true,
            predictions,
            zero_division=0,
        )

        balanced_accuracy = balanced_accuracy_score(
            y_true,
            predictions,
        )

        results.append(
            {
                "threshold": threshold,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "balanced_accuracy": balanced_accuracy,
            }
        )

    results_df = pd.DataFrame(results)

    print("=" * 80)
    print("CODEATLAS - THRESHOLD ANALYSIS")
    print("=" * 80)

    print(
        results_df.to_string(
            index=False,
            formatters={
                "threshold": "{:.2f}".format,
                "precision": "{:.3f}".format,
                "recall": "{:.3f}".format,
                "f1": "{:.3f}".format,
                "balanced_accuracy": "{:.3f}".format,
            },
        )
    )

    print("\n" + "=" * 80)
    print("BEST THRESHOLD BY F1")
    print("=" * 80)

    best = results_df.loc[
        results_df["f1"].idxmax()
    ]

    print(f"Threshold:         {best['threshold']:.2f}")
    print(f"Precision:         {best['precision']:.3f}")
    print(f"Recall:            {best['recall']:.3f}")
    print(f"F1:                {best['f1']:.3f}")
    print(f"Balanced Accuracy: {best['balanced_accuracy']:.3f}")


if __name__ == "__main__":
    main()