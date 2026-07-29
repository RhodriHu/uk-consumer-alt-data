"""
Load DfT port freight data (Tonnage Inwards) and convert to a clean
quarterly time series of container-heavy UK port imports.

Data source: DfT PORT0502 quarterly statistics.
We use inbound tonnage as a proxy for UK import activity, which is
relevant to the consumer stocks in our universe (imported inventory
for fashion, food, and general retail).
"""

import pandas as pd
import os

filepath = "data/raw/port0502.ods"

# We want inbound tonnage - imports into the UK, which is what drives
# consumer retail inventory. Outbound is exports which doesn't fit our thesis.
sheet = "Tonnage_(Inwards)"

# The five container-heavy ports that matter for consumer imports.
# Others (Aberdeen, Sullom Voe) are oil/gas focused and irrelevant.
container_ports = [
    "Felixstowe",              # UK's largest container port
    "London",                   # Includes London Gateway and Tilbury
    "Southampton",              # Major container hub
    "Grimsby and Immingham",    # Vehicle imports, general cargo
    "Liverpool",                # Major container port
]

# Load the sheet with no header assumption
df = pd.read_excel(filepath, sheet_name=sheet, engine="odf", header=None)

# Row 7 (index 6) has the column headers (quarter labels)
# Rows 8+ (index 7+) have port data
headers = df.iloc[6].tolist()
df.columns = headers
df = df.iloc[7:].reset_index(drop=True)

# Set the port name column as the index so we can look up ports by name
df = df.set_index("Major Port")

# Keep only container ports we care about
df = df.loc[container_ports]

# Keep only columns that look like quarters (start with "20")
# This drops the junk columns at the end (percentage changes, four-quarter totals)
quarter_cols = [c for c in df.columns if str(c).startswith("20")]
df = df[quarter_cols]

# Clean up quarter labels - remove "[Note X]" suffixes and trailing spaces
df.columns = [str(c).split("[")[0].strip() for c in df.columns]

# Convert all values to numeric (some might be strings like "z" for missing)
df = df.apply(pd.to_numeric, errors="coerce")

# Transpose so quarters are rows and ports are columns (easier to work with)
df = df.T

# Compute total container port imports each quarter across all 5 ports
df["Total_Container_Imports"] = df.sum(axis=1)

# Convert quarter labels (e.g. "2020 Q1") to proper datetime (start of quarter)
# pandas PeriodIndex needs "2009Q1" format (no space), not "2009 Q1"
quarter_labels = [str(q).replace(" ", "") for q in df.index]
df.index = pd.PeriodIndex(quarter_labels, freq="Q").to_timestamp()
df.index.name = "date"

# Save the clean dataset
output_path = "data/processed/port_freight_quarterly.csv"
os.makedirs("data/processed", exist_ok=True)
df.to_csv(output_path)

print(f"Saved port freight data to {output_path}")
print(f"Shape: {df.shape} (quarters x ports)")
print(f"\nFirst 5 quarters:")
print(df.head())
print(f"\nLast 5 quarters:")
print(df.tail())
print(f"\nCovers {df.index[0].date()} to {df.index[-1].date()}")