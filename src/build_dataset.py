"""
Combine price, trends, port freight, and ONS retail sales data into
one aligned monthly dataset.

Since Google Trends is our lowest-frequency signal (monthly), we resample
everything to month-end frequency.

Port freight is quarterly - we forward-fill so each month gets the most
recently released quarter's value.

ONS retail sales is monthly but published with a ~1 month lag - we shift
by 1 month so signals only use data actually available at decision time.
"""

import pandas as pd
import os

# ==============================================================
# 1. Load and aggregate price data to monthly
# ==============================================================

tickers = ["GRG.L", "NXT.L", "JD.L", "DOM.L", "JDW.L", "BME.L", "MKS.L"]

# Map each stock to its ONS retail category
# Imperfect but pragmatic - documented in README
stock_to_category = {
    "GRG.L": "food_yoy",       # Greggs = food
    "MKS.L": "food_yoy",       # M&S = mixed but food-dominant
    "DOM.L": "food_yoy",       # Domino's = food-adjacent (delivery)
    "JDW.L": "food_yoy",       # Wetherspoons = pub food (imperfect)
    "NXT.L": "clothing_yoy",   # Next = fashion
    "JD.L": "clothing_yoy",    # JD Sports = sportswear
    "BME.L": "household_yoy",  # B&M = household/discount
}

print("Loading price data...")
prices_monthly = pd.DataFrame()

for ticker in tickers:
    filename = f"data/raw/{ticker.replace('.L', '').lower()}_prices.csv"
    df = pd.read_csv(filename, skiprows=3, header=None)
    df.columns = ["date", "close", "high", "low", "open", "volume"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    monthly_close = df["close"].resample("ME").last()
    prices_monthly[ticker] = monthly_close

print(f"  Monthly prices shape: {prices_monthly.shape}")

returns_monthly = prices_monthly.pct_change()

# ==============================================================
# 2. Load Google Trends
# ==============================================================

print("Loading trends data...")
trends = pd.read_csv("data/processed/trends_combined.csv", index_col="date", parse_dates=True)
trends.index = trends.index + pd.offsets.MonthEnd(0)
print(f"  Trends shape: {trends.shape}")

# ==============================================================
# 3. Load port freight
# ==============================================================

print("Loading port freight data...")
port = pd.read_csv("data/processed/port_freight_quarterly.csv", index_col="date", parse_dates=True)
port_total = port[["Total_Container_Imports"]]
port_monthly = port_total.resample("ME").ffill()
print(f"  Port freight monthly shape: {port_monthly.shape}")

# ==============================================================
# 4. Load ONS retail sales - APPLY PUBLICATION LAG
# ==============================================================

print("Loading ONS retail sales data...")
ons = pd.read_csv("data/processed/ons_retail_sales.csv", index_col="date", parse_dates=True)

# CRITICAL: ONS publishes month M data in month M+1 (roughly week 3).
# So on 30 April, most recent available data is March. To respect this,
# shift the index forward by 1 month - each month's row now shows the
# data that was actually publicly available by month-end.
ons_lagged = ons.copy()
ons_lagged.index = ons_lagged.index + pd.offsets.MonthEnd(1)

print(f"  ONS shape: {ons.shape}")
print(f"  Lagged so each month shows data available at decision time")

# ==============================================================
# 5. Combine into master dataset
# ==============================================================

print("Combining all data...")

returns_cols = returns_monthly.copy()
returns_cols.columns = [f"return_{c}" for c in returns_cols.columns]

trends_cols = trends.copy()
trends_cols.columns = [f"trends_{c}" for c in trends_cols.columns]

# Build stock-specific ONS column for each ticker based on category mapping
ons_stock = pd.DataFrame(index=ons_lagged.index)
for ticker, category in stock_to_category.items():
    ons_stock[f"ons_{ticker}"] = ons_lagged[category]

master = (
    returns_cols
    .join(trends_cols, how="inner")
    .join(port_monthly, how="inner")
    .join(ons_stock, how="inner")
)

master = master.dropna()

output_path = "data/processed/master_dataset.csv"
os.makedirs("data/processed", exist_ok=True)
master.to_csv(output_path)

print(f"\nMaster dataset saved to {output_path}")
print(f"Shape: {master.shape} (months x variables)")
print(f"Coverage: {master.index[0].date()} to {master.index[-1].date()}")
print(f"\nColumn list:")
for col in master.columns:
    print(f"  - {col}")