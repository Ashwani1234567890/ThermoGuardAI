
import pandas as pd
import joblib

from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# Project paths
DATA_FILE = Path("data/processed/SKAB/skab_anomaly_dataset.csv")
MODEL_DIR = Path("models/trained_model")
REPORT_DIR = Path("reports/SKAB")

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Load processed SKAB dataset
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

# Chronological split separately for each valve
train_parts = []
test_parts = []

for source, group in df.groupby("source_file", sort=False):
    split_index = int(len(group) * 0.8)
    train_parts.append(group.iloc[:split_index])
    test_parts.append(group.iloc[split_index:])

train_df = pd.concat(train_parts)
test_df = pd.concat(test_parts)

X_train = train_df[features]
y_train = train_df["anomaly"].astype(int)

X_test = test_df[features]
y_test = test_df["anomaly"].astype(int)

print("Training records:", len(X_train))
print("Testing records:", len(X_test))

# Build Gradient Boosting classifier
model = GradientBoostingClassifier(
    n_estimators=150,
    learning_rate=0.05,
    max_depth=3,
    random_state=42
)

# Train model
model.fit(X_train, y_train)

# Predict
predictions = model.predict(X_test)

# Evaluate
accuracy = accuracy_score(y_test, predictions)

print("\nGRADIENT BOOSTING ACCURACY:",
      round(accuracy * 100, 2), "%")

report = classification_report(
    y_test,
    predictions,
    zero_division=0
)

print("\nCLASSIFICATION REPORT:")
print(report)

matrix = confusion_matrix(y_test, predictions)

print("\nCONFUSION MATRIX:")
print(matrix)

# Save model
model_path = MODEL_DIR / "skab_gradient_boosting.pkl"
joblib.dump(model, model_path)

# Save evaluation report
report_path = REPORT_DIR / "skab_gradient_boosting_evaluation.txt"

with open(report_path, "w", encoding="utf-8") as file:
    file.write("SKAB GRADIENT BOOSTING EVALUATION\n\n")
    file.write(f"Training records: {len(X_train)}\n")
    file.write(f"Testing records: {len(X_test)}\n")
    file.write(f"Accuracy: {accuracy:.4f}\n\n")
    file.write(report)
    file.write("\n\nConfusion Matrix:\n")
    file.write(str(matrix))

print("\nGradient Boosting training completed!")
print("Model saved:", model_path)
print("Report saved:", report_path)
