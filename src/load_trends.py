"""
Load Google Trends CSV files (manually downloaded from trends.google.com)
and combine them into a single clean weekly dataset.

Google Trends CSVs have junk header rows we need to skip.
The interest values are 0-100 relative search volume.
"""

import pandas as pd
import os

# Map each ticker to the filename we saved
trends_files = {
    "GRG.L": "data/raw/grg_trends.csv",
    "NXT.L": "data/raw/nxt_trends.csv",
    "JD.L": "data/raw/jd_trends.csv",
    "DOM.L": "data/raw/dom_trends.csv",
    "JDW.L": "data/raw/jdw_trends.csv",
    "BME.L": "data/raw/bme_trends.csv",
    "MKS.L": "data/raw/mks_trends.csv",
}

# Start with an empty DataFrame - we'll build up columns one stock at a time
combined = pd.DataFrame()

for ticker, filepath in trends_files.items():
    print(f"Loading {ticker} from {filepath}...")

    # skiprows=2 skips Google's junk header rows
    # The first data row has "Week" as column header, then dates below
    df = pd.read_csv(filepath, skiprows=2)

    # Rename columns to standardise: first col is date, second is search interest
    df.columns = ["date", ticker]

    # Convert date column to proper datetime
    df["date"] = pd.to_datetime(df["date"])

    # Set date as index so we can merge on it later
    df = df.set_index("date")

    # Convert the search values to numeric. Google sometimes puts "<1" for
    # very low values - we treat those as 0.
    df[ticker] = pd.to_numeric(df[ticker], errors="coerce").fillna(0)

    # Merge this stock's column into the combined DataFrame
    if combined.empty:
        combined = df
    else:
        combined = combined.join(df, how="outer")

    print(f"  {len(df)} weeks loaded")

# Sort by date just to be safe
combined = combined.sort_index()

# Save the clean combined dataset
output_path = "data/processed/trends_combined.csv"
os.makedirs("data/processed", exist_ok=True)
combined.to_csv(output_path)

print(f"\nDone. Combined dataset saved to {output_path}")
print(f"Shape: {combined.shape} (weeks x stocks)")
print(f"\nFirst 5 rows:")
print(combined.head())
print(f"\nLast 5 rows:")
print(combined.tail())