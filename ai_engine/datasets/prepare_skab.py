
import pandas as pd
from pathlib import Path

# SKAB dataset location
DATA_DIR = Path("data/raw/SKAB/waico-SKAB-b2c0d46/data")

# Output location
OUTPUT_DIR = Path("data/processed/SKAB")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Files to process
FILES = [
    DATA_DIR / "valve1/0.csv",
    DATA_DIR / "valve2/0.csv",
]

processed_data = []

for file in FILES:
    df = pd.read_csv(file, sep=";")

    # Keep numerical sensor measurements
    sensor_columns = [
        "Accelerometer1RMS",
        "Accelerometer2RMS",
        "Current",
        "Pressure",
        "Temperature",
        "Thermocouple",
        "Voltage",
        "Volume Flow RateRMS",
    ]

    selected = df[sensor_columns + ["anomaly"]].copy()

    # Identify the original source file
    selected["source_file"] = file.parent.name + "_" + file.name

    processed_data.append(selected)

# Combine both datasets
final_df = pd.concat(processed_data, ignore_index=True)

# Save processed dataset
output_file = OUTPUT_DIR / "skab_anomaly_dataset.csv"
final_df.to_csv(output_file, index=False)

print("SKAB preprocessing completed!")
print("Total records:", len(final_df))
print("Total columns:", len(final_df.columns))
print("\nAnomaly distribution:")
print(final_df["anomaly"].value_counts())
print("\nSaved to:", output_file)
