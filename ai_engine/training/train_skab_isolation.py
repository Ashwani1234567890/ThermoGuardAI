
import pandas as pd
import joblib

from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)

# Project paths
DATA_FILE = Path("data/processed/SKAB/skab_anomaly_dataset.csv")
MODEL_DIR = Path("models/trained_model")
REPORT_DIR = Path("reports/SKAB")

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Load dataset
df = pd.read_csv(DATA_FILE)

# Sensor features
features = [
    "Accelerometer1RMS",
    "Accelerometer2RMS",
    "Current",
    "Pressure",
    "Temperature",
    "Thermocouple",
    "Voltage",
    "Volume Flow RateRMS"
]

# Chronological train/test split within each valve
train_parts = []
test_parts = []

for source, group in df.groupby("source_file", sort=False):
    split_index = int(len(group) * 0.8)
    train_parts.append(group.iloc[:split_index])
    test_parts.append(group.iloc[split_index:])

train_df = pd.concat(train_parts)
test_df = pd.concat(test_parts)

# Keep only normal observations for model training and calibration
normal_train = train_df[train_df["anomaly"] == 0]

# Split normal records chronologically:
# First 80% for model training, last 20% for calibration
model_train_parts = []
calibration_parts = []

for source, group in normal_train.groupby("source_file", sort=False):
    split_index = int(len(group) * 0.8)

    model_train_parts.append(group.iloc[:split_index])
    calibration_parts.append(group.iloc[split_index:])

model_train_df = pd.concat(model_train_parts)
calibration_df = pd.concat(calibration_parts)

X_train = model_train_df[features]
X_calibration = calibration_df[features]

X_test = test_df[features]
y_test = test_df["anomaly"].astype(int)

print("Model training records:", len(X_train))
print("Normal calibration records:", len(X_calibration))
print("Testing records:", len(X_test))

print("Normal training records:", len(X_train))
print("Testing records:", len(X_test))

# Build model pipeline
model = Pipeline([
    ("scaler", StandardScaler()),
    ("isolation_forest", IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
        n_jobs=-1
    ))
])

# Train
model.fit(X_train)

# Calculate anomaly scores
# Higher scores indicate more anomalous observations
calibration_scores = -model.decision_function(X_calibration)
test_scores = -model.decision_function(X_test)

# Use the 99th percentile of normal calibration scores
threshold = pd.Series(calibration_scores).quantile(0.99)

# Predict anomalies on untouched test data
predictions = (test_scores >= threshold).astype(int)

print("\nCALIBRATED ANOMALY THRESHOLD:", threshold)

print("\nCALIBRATED ANOMALY THRESHOLD:", threshold)

# Anomaly score analysis
score_analysis = pd.DataFrame({
    "actual_anomaly": y_test.values,
    "anomaly_score": test_scores
})

print("\nANOMALY SCORE DISTRIBUTION:")
print(
    score_analysis.groupby("actual_anomaly")["anomaly_score"]
    .agg(["count", "mean", "min", "median", "max"])
)

score_analysis.to_csv(
    REPORT_DIR / "skab_isolation_anomaly_scores.csv",
    index=False
)

# Evaluation
accuracy = accuracy_score(y_test, predictions)

print("\nMODEL ACCURACY:", round(accuracy * 100, 2), "%")

print("\nCLASSIFICATION REPORT:")
report = classification_report(
    y_test,
    predictions,
    zero_division=0
)
print(report)

matrix = confusion_matrix(y_test, predictions)

print("\nCONFUSION MATRIX:")
print(matrix)

# Save model
model_path = MODEL_DIR / "skab_isolation_forest.pkl"
joblib.dump(model, model_path)

# Save evaluation
report_path = REPORT_DIR / "skab_isolation_evaluation.txt"

with open(report_path, "w", encoding="utf-8") as file:
    file.write("SKAB ISOLATION FOREST EVALUATION\n\n")
    file.write(f"Normal training records: {len(X_train)}\n")
    file.write(f"Testing records: {len(X_test)}\n")
    file.write(f"Accuracy: {accuracy:.4f}\n\n")
    file.write(report)
    file.write("\n\nConfusion Matrix:\n")
    file.write(str(matrix))

print("\nIsolation Forest training completed!")
print("Model saved:", model_path)
print("Report saved:", report_path)
