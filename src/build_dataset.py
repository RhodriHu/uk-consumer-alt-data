"""
Combine price, trends, and port freight data into one aligned monthly dataset.

Since Google Trends is our lowest-frequency signal (monthly), we resample
everything to month-end frequency.

Port freight is quarterly - we forward-fill so each month gets the most
recently released quarter's value. This is realistic: if you're standing
on 15 March 2024, you know Q4 2023's port freight (published ~10 weeks
after quarter end).
"""

import pandas as pd
import os

# ==============================================================
# 1. Load and aggregate price data to monthly
# ==============================================================

tickers = ["GRG.L", "NXT.L", "JD.L", "DOM.L", "JDW.L", "BME.L", "MKS.L"]

print("Loading price data...")
prices_monthly = pd.DataFrame()

for ticker in tickers:
    filename = f"data/raw/{ticker.replace('.L', '').lower()}_prices.csv"
    # yfinance CSVs have 3 header rows we skip
    df = pd.read_csv(filename, skiprows=3, header=None)
    df.columns = ["date", "close", "high", "low", "open", "volume"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Resample daily prices to month-end closing price
    monthly_close = df["close"].resample("ME").last()
    prices_monthly[ticker] = monthly_close

print(f"  Monthly prices shape: {prices_monthly.shape}")

# Compute monthly returns (this is what we'll actually trade on)
returns_monthly = prices_monthly.pct_change()

# ==============================================================
# 2. Load Google Trends data (already monthly)
# ==============================================================

print("Loading trends data...")
trends = pd.read_csv("data/processed/trends_combined.csv", index_col="date", parse_dates=True)

# Trends CSV dates might be first-of-month; convert to month-end for consistency
trends.index = trends.index + pd.offsets.MonthEnd(0)
print(f"  Trends shape: {trends.shape}")

# ==============================================================
# 3. Load port freight, upsample from quarterly to monthly
# ==============================================================

print("Loading port freight data...")
port = pd.read_csv("data/processed/port_freight_quarterly.csv", index_col="date", parse_dates=True)

# Keep just the total imports column - individual ports were for validation
port_total = port[["Total_Container_Imports"]]

# Convert quarterly index to month-end and forward-fill
# This gives us each month the most recent released quarterly value
port_monthly = port_total.resample("ME").ffill()
print(f"  Port freight monthly shape: {port_monthly.shape}")

# ==============================================================
# 4. Combine everything into master dataset
# ==============================================================

print("Combining all data...")

# Start with returns (main variable of interest)
# Prefix column names so we know what's what
returns_cols = returns_monthly.copy()
returns_cols.columns = [f"return_{c}" for c in returns_cols.columns]

trends_cols = trends.copy()
trends_cols.columns = [f"trends_{c}" for c in trends_cols.columns]

# Join everything on the date index (inner join = only dates where all data exists)
master = returns_cols.join(trends_cols, how="inner").join(port_monthly, how="inner")

# Drop rows with any NaN (e.g. first month has no return)
master = master.dropna()

# Save it
output_path = "data/processed/master_dataset.csv"
os.makedirs("data/processed", exist_ok=True)
master.to_csv(output_path)

print(f"\nMaster dataset saved to {output_path}")
print(f"Shape: {master.shape} (months x variables)")
print(f"Coverage: {master.index[0].date()} to {master.index[-1].date()}")
print(f"\nColumn list:")
for col in master.columns:
    print(f"  - {col}")
print(f"\nFirst 3 rows:")
print(master.head(3))