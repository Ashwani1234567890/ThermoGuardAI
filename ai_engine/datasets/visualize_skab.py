
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load processed SKAB dataset
file_path = Path("data/processed/SKAB/skab_anomaly_dataset.csv")
df = pd.read_csv(file_path)

# Create output folder
output_dir = Path("reports/SKAB")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Plot normal vs anomalous records
label_counts = df["anomaly"].value_counts().sort_index()

plt.figure(figsize=(7, 5))
label_counts.plot(kind="bar")
plt.title("SKAB Normal vs Anomalous Records")
plt.xlabel("Anomaly Label (0 = Normal, 1 = Anomaly)")
plt.ylabel("Number of Records")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(output_dir / "anomaly_distribution.png")
plt.close()

# 2. Plot temperature distribution
plt.figure(figsize=(8, 5))

for label, group in df.groupby("anomaly"):
    plt.hist(
        group["Temperature"],
        bins=40,
        alpha=0.5,
        label=f"Anomaly {int(label)}"
    )

plt.title("SKAB Temperature Distribution")
plt.xlabel("Temperature")
plt.ylabel("Frequency")
plt.legend()
plt.tight_layout()
plt.savefig(output_dir / "temperature_distribution.png")
plt.close()

print("SKAB visualizations generated successfully!")
print("Saved in:", output_dir)
print("\nGenerated files:")
print("- anomaly_distribution.png")
print("- temperature_distribution.png")
