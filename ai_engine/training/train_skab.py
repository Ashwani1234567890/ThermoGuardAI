
import pandas as pd
import joblib

from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
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

# Load processed dataset
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

target = "anomaly"

# Split each valve's time series chronologically:
# First 80% for training, final 20% for testing.
train_parts = []
test_parts = []

for source, group in df.groupby("source_file", sort=False):
    split_index = int(len(group) * 0.8)

    train_parts.append(group.iloc[:split_index])
    test_parts.append(group.iloc[split_index:])

train_df = pd.concat(train_parts)
test_df = pd.concat(test_parts)

X_train = train_df[features]
y_train = train_df[target]

X_test = test_df[features]
y_test = test_df[target]

print("Training records:", len(X_train))
print("Testing records:", len(X_test))

# Train Random Forest
model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

model.fit(X_train, y_train)

# Evaluate model
predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nMODEL ACCURACY:", round(accuracy * 100, 2), "%")

print("\nCLASSIFICATION REPORT:")
report = classification_report(
    y_test,
    predictions,
    zero_division=0
)
print(report)

print("\nCONFUSION MATRIX:")
matrix = confusion_matrix(y_test, predictions)
print(matrix)

# Save trained model
model_path = MODEL_DIR / "skab_random_forest.pkl"
joblib.dump(model, model_path)

# Save evaluation report
report_path = REPORT_DIR / "skab_model_evaluation.txt"

with open(report_path, "w", encoding="utf-8") as file:
    file.write("SKAB RANDOM FOREST EVALUATION\n\n")
    file.write(f"Training records: {len(X_train)}\n")
    file.write(f"Testing records: {len(X_test)}\n")
    file.write(f"Accuracy: {accuracy:.4f}\n\n")
    file.write(report)
    file.write("\n\nConfusion Matrix:\n")
    file.write(str(matrix))

print("\nTraining completed successfully!")
print("Model saved to:", model_path)
print("Evaluation saved to:", report_path)
