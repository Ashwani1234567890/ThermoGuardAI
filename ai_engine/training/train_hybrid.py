
import pandas as pd
import numpy as np
import joblib

from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ---------------------------------
# PROJECT PATHS
# ---------------------------------

DATA_PATH = Path("data/processed/thermal_feature_dataset.csv")
MODEL_DIR = Path("models/trained_model")
REPORT_DIR = Path("reports/thermal")

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------
# LOAD DATASET
# ---------------------------------

df = pd.read_csv(DATA_PATH)

print("HYBRID THERMAL MODEL TRAINING")
print("--------------------------------")

print("Dataset shape:", df.shape)

# ---------------------------------
# SELECT ALL FEATURES
# ---------------------------------

HYBRID_FEATURES = [
    "mean_temperature",
    "max_temperature",
    "min_temperature",
    "spatial_range",
    "spatial_std",
    "max_sensor_mean",
    "min_sensor_mean",
    "mean_rate_of_change",
    "max_rate_of_change",
    "min_rate_of_change",
    "temporal_std",
    "overall_temperature_rise",
    "most_stable_sensor_std",
    "noisiest_sensor_std",
    "sensor_variation_range",
    "stuck_sensor_count"
]

X = df[HYBRID_FEATURES]
y = df["label"]

# ---------------------------------
# SPLIT BY SCENARIO
# ---------------------------------

scenario_labels = (
    df.groupby("scenario_id")["label"]
    .first()
)

scenario_ids = scenario_labels.index.to_numpy()
scenario_classes = scenario_labels.to_numpy()

train_ids, test_ids = train_test_split(
    scenario_ids,
    test_size=0.20,
    random_state=42,
    stratify=scenario_classes
)

train_df = df[df["scenario_id"].isin(train_ids)]
test_df = df[df["scenario_id"].isin(test_ids)]

X_train = train_df[HYBRID_FEATURES]
y_train = train_df["label"]

X_test = test_df[HYBRID_FEATURES]
y_test = test_df["label"]

print("\nTraining scenarios:", len(train_ids))
print("Testing scenarios:", len(test_ids))

# ---------------------------------
# MODEL 1: RANDOM FOREST
# ---------------------------------

rf_model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

rf_model.fit(X_train, y_train)

rf_predictions = rf_model.predict(X_test)

rf_accuracy = accuracy_score(
    y_test,
    rf_predictions
)

# ---------------------------------
# MODEL 2: EXTRA TREES
# ---------------------------------

extra_model = ExtraTreesClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

extra_model.fit(X_train, y_train)

extra_predictions = extra_model.predict(X_test)

extra_accuracy = accuracy_score(
    y_test,
    extra_predictions
)

# ---------------------------------
# EVALUATION
# ---------------------------------

print("\nRANDOM FOREST ACCURACY:")
print(round(rf_accuracy * 100, 2), "%")

print("\nRANDOM FOREST CLASSIFICATION REPORT:")

rf_report = classification_report(
    y_test,
    rf_predictions,
    zero_division=0
)

print(rf_report)

print("\nRANDOM FOREST CONFUSION MATRIX:")

print(confusion_matrix(
    y_test,
    rf_predictions,
    labels=rf_model.classes_
))

print("\nEXTRA TREES ACCURACY:")
print(round(extra_accuracy * 100, 2), "%")

print("\nEXTRA TREES CLASSIFICATION REPORT:")

extra_report = classification_report(
    y_test,
    extra_predictions,
    zero_division=0
)

print(extra_report)

print("\nEXTRA TREES CONFUSION MATRIX:")

print(confusion_matrix(
    y_test,
    extra_predictions,
    labels=extra_model.classes_
))

# ---------------------------------
# FEATURE IMPORTANCE
# ---------------------------------

print("\nHYBRID RANDOM FOREST FEATURE IMPORTANCE:")

for name, importance in sorted(
    zip(HYBRID_FEATURES, rf_model.feature_importances_),
    key=lambda item: item[1],
    reverse=True
):
    print(f"{name}: {importance:.4f}")

# ---------------------------------
# SAVE MODELS
# ---------------------------------

joblib.dump(
    rf_model,
    MODEL_DIR / "thermal_hybrid_random_forest.pkl"
)

joblib.dump(
    extra_model,
    MODEL_DIR / "thermal_hybrid_extra_trees.pkl"
)

# ---------------------------------
# SAVE REPORT
# ---------------------------------

report_path = REPORT_DIR / "hybrid_model_evaluation.txt"

with open(report_path, "w", encoding="utf-8") as file:

    file.write("HYBRID THERMAL MODEL EVALUATION\n")
    file.write("================================\n\n")

    file.write(f"Dataset shape: {df.shape}\n")
    file.write(f"Training scenarios: {len(train_ids)}\n")
    file.write(f"Testing scenarios: {len(test_ids)}\n\n")

    file.write("RANDOM FOREST\n")
    file.write(f"Accuracy: {rf_accuracy * 100:.2f}%\n\n")
    file.write(rf_report)

    file.write("\n\nEXTRA TREES\n")
    file.write(f"Accuracy: {extra_accuracy * 100:.2f}%\n\n")
    file.write(extra_report)

print("\nHYBRID MODELS SAVED SUCCESSFULLY")
print("Evaluation report:", report_path)
