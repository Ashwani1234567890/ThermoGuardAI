import pandas as pd
from pathlib import Path

DATA = Path("data/raw/SKAB/waico-SKAB-b2c0d46/data")
FILES = [DATA / "anomaly-free/anomaly-free.csv", DATA / "valve1/0.csv", DATA / "valve2/0.csv"]

for file in FILES:
    df = pd.read_csv(file, sep=";")
    print("\\nFILE:", file)
    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())
    print("Missing values:", df.isnull().sum().sum())
    if "anomaly" in df.columns:
        print("Anomaly labels:")
        print(df["anomaly"].value_counts())
