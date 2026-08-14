"""
Load ONS retail sales data, filter to relevant categories and measure,
and produce a monthly time series of YoY sales growth per category.

Data source: ONS Retail Sales Index (dataset ID: DRSI).
Measure used: Chained volume percentage change on same month a year earlier
(standard measure of real retail sales growth).

Publication lag: ONS publishes data for month M in the 3rd or 4th week of
month M+1. When building signals we account for this lag so we don't use
data before it was publicly available.
"""

import pandas as pd
import os
import requests

# ==============================================================
# 1. Download raw data if not cached
# ==============================================================

url = "https://download.ons.gov.uk/downloads/datasets/retail-sales-index/editions/time-series/versions/45.csv"
local_path = "data/raw/ons_retail_sales_full.csv"
os.makedirs("data/raw", exist_ok=True)

if not os.path.exists(local_path):
    print(f"Downloading ONS data from {url}...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(response.content)
    print(f"Saved {len(response.content) / 1e6:.1f} MB")
else:
    print(f"Using cached file at {local_path}")

# ==============================================================
# 2. Load and filter
# ==============================================================

print("Loading and filtering...")
df = pd.read_csv(local_path)

# Filter to the specific measure we want:
# Chained volume (strips inflation) YoY % change (captures momentum)
measure = "Chained volume - Percentage change on same month a year earlier"

# We only want seasonally adjusted data for cleaner comparisons
df = df[
    (df["Prices"] == measure)
    & (df["SeasonalAdjustment"] == "Seasonally Adjusted")
].copy()

# Filter to the three categories that map to our stock universe
target_categories = [
    "Predominantly food stores",
    "Textile, clothing and footwear stores",
    "Household goods stores",
]

df = df[df["UnofficialStandardIndustrialClassification"].isin(target_categories)]

# Keep just the columns we need
df = df[["mmm-yy", "UnofficialStandardIndustrialClassification", "v4_1"]]
df.columns = ["date", "category", "yoy_growth"]

# Convert "mmm-yy" (e.g. "Jan-26") to proper datetime (month-end)
df["date"] = pd.to_datetime(df["date"], format="%b-%y")
# Shift to month-end so it aligns with our other data
df["date"] = df["date"] + pd.offsets.MonthEnd(0)

# Pivot to wide format: rows = dates, columns = categories
wide = df.pivot(index="date", columns="category", values="yoy_growth")
wide = wide.sort_index()

# Rename columns to shorter, code-friendly names
wide.columns = ["food_yoy", "household_yoy", "clothing_yoy"]

# Reorder for consistency
wide = wide[["food_yoy", "clothing_yoy", "household_yoy"]]

# ==============================================================
# 3. Save
# ==============================================================

output_path = "data/processed/ons_retail_sales.csv"
os.makedirs("data/processed", exist_ok=True)
wide.to_csv(output_path)

print(f"\nSaved to {output_path}")
print(f"Shape: {wide.shape}")
print(f"Coverage: {wide.index[0].date()} to {wide.index[-1].date()}")
print(f"\nLast 6 months:")
print(wide.tail(6))