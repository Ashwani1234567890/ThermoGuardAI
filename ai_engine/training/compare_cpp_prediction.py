
import joblib
import pandas as pd
import numpy as np
import subprocess

MODEL_PATH = "models/trained_model/thermal_hybrid_extra_trees.pkl"
DATA_PATH = "data/processed/thermal_validation_features.csv"
CPP_PROGRAM = "firmware/test_thermal_inference.exe"

print("Loading trained Extra Trees model...")

model = joblib.load(MODEL_PATH)
data = pd.read_csv(DATA_PATH)

feature_names = list(model.feature_names_in_)
X = data[feature_names].to_numpy(dtype=float)

print("Total validation scenarios:", len(X))

# Generate input for the C++ executable.
input_lines = []

for row in X:
    input_lines.append(
        " ".join(format(float(value), ".17g") for value in row)
    )

input_data = "\n".join(input_lines) + "\n"

print("Running C++ inference engine...")

result = subprocess.run(
    [CPP_PROGRAM],
    input=input_data,
    text=True,
    capture_output=True,
    check=True
)

# Read C++ predictions and probabilities.
cpp_lines = result.stdout.strip().splitlines()

if len(cpp_lines) != len(X):
    raise RuntimeError(
        f"Expected {len(X)} predictions, got {len(cpp_lines)}"
    )

cpp_predictions = []
cpp_probabilities = []

for line in cpp_lines:
    values = [float(value) for value in line.split()]

    if len(values) != 6:
        raise RuntimeError("Invalid C++ prediction output: " + line)

    cpp_predictions.append(int(values[0]))
    cpp_probabilities.append(values[1:])

cpp_predictions = np.array(cpp_predictions)
cpp_probabilities = np.array(cpp_probabilities)

# Generate original Python predictions.
print("Running Python model...")

python_predictions = model.predict(X)
python_probabilities = model.predict_proba(X)

python_class_indices = np.array([
    np.where(model.classes_ == label)[0][0]
    for label in python_predictions
])

# Compare predictions.
prediction_matches = (
    cpp_predictions == python_class_indices
)

agreement = np.mean(prediction_matches) * 100

# Compare probability differences.
absolute_differences = np.abs(
    python_probabilities - cpp_probabilities
)

max_difference = np.max(absolute_differences)
mean_difference = np.mean(absolute_differences)

# Compare against actual validation labels.
actual_labels = data["label"].to_numpy()

cpp_class_names = model.classes_[cpp_predictions]

cpp_accuracy = np.mean(
    cpp_class_names == actual_labels
) * 100

python_accuracy = np.mean(
    python_predictions == actual_labels
) * 100

print("\n====================================")
print("C++ vs PYTHON MODEL VALIDATION")
print("====================================")

print("Total scenarios:", len(X))
print(f"Prediction agreement: {agreement:.2f}%")
print(f"Python validation accuracy: {python_accuracy:.2f}%")
print(f"C++ validation accuracy: {cpp_accuracy:.2f}%")
print(f"Maximum probability difference: {max_difference:.10f}")
print(f"Mean probability difference: {mean_difference:.10f}")

print("\nPrediction mismatches:", np.sum(~prediction_matches))

print("\nC++ EXECUTION DETAILS")
print(result.stderr.strip())

if agreement == 100.0 and max_difference < 0.00001:
    print("\nSUCCESS: C++ inference matches Python.")
else:
    print("\nWARNING: Differences detected. Investigate before deployment.")
