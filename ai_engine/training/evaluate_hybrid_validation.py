
from pathlib import Path
import joblib
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# Project paths
VALIDATION_PATH = Path("data/processed/thermal_validation_features.csv")

MODEL_PATHS = {
    "Hybrid Random Forest": Path(
        "models/trained_model/thermal_hybrid_random_forest.pkl"
    ),
    "Hybrid Extra Trees": Path(
        "models/trained_model/thermal_hybrid_extra_trees.pkl"
    )
}

REPORT_PATH = Path("reports/thermal/hybrid_independent_validation.txt")

# Load independent validation dataset
df = pd.read_csv(VALIDATION_PATH)

X_all = df.drop(columns=["scenario_id", "label"])
y = df["label"]

report = []

report.append("HYBRID MODEL - INDEPENDENT VALIDATION")
report.append("=" * 55)
report.append(f"Validation scenarios: {len(df)}")
report.append(f"Feature count: {X_all.shape[1]}")
report.append("\nClass distribution:")
report.append(y.value_counts().to_string())

# Evaluate each trained model
for model_name, model_path in MODEL_PATHS.items():

    model = joblib.load(model_path)

    # Match the exact feature order used during training
    if hasattr(model, "feature_names_in_"):
        feature_names = list(model.feature_names_in_)
    else:
        feature_names = list(X_all.columns)

    missing_features = set(feature_names) - set(X_all.columns)

    if missing_features:
        raise ValueError(
            f"Missing features for {model_name}: {missing_features}"
        )

    X = X_all[feature_names]

    predictions = model.predict(X)

    accuracy = accuracy_score(y, predictions)

    class_labels = model.classes_

    matrix = confusion_matrix(
        y,
        predictions,
        labels=class_labels
    )

    class_report = classification_report(
        y,
        predictions,
        labels=class_labels,
        zero_division=0
    )

    report.append("\n\n" + "=" * 55)
    report.append(model_name.upper())
    report.append("=" * 55)

    report.append(f"\nAccuracy: {accuracy * 100:.2f}%")

    report.append("\nClassification Report:")
    report.append(class_report)

    report.append("\nConfusion Matrix:")
    report.append(str(matrix))

    print(f"\n{model_name}")
    print("-" * 40)
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print(class_report)
    print("Confusion Matrix:")
    print(matrix)

# Save report
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

REPORT_PATH.write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\nINDEPENDENT VALIDATION COMPLETED")
print(f"Report saved to: {REPORT_PATH}")
