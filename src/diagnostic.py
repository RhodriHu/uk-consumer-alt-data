"""
Diagnostic chart: rolling 12-month correlation between the composite
signal and next-month returns across all stocks in the universe.

Purpose: test whether the signal had predictive power at any point,
and identify when (if ever) that predictive power decayed.

A positive correlation means high-signal stocks tended to have
higher next-month returns - the strategy's core hypothesis.
Zero or negative correlation means the signal wasn't working.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# ==============================================================
# Load the master dataset (already built by build_dataset.py)
# ==============================================================

master = pd.read_csv(
    "data/processed/master_dataset.csv",
    index_col="date",
    parse_dates=True,
)

tickers = ["GRG.L", "NXT.L", "JD.L", "DOM.L", "JDW.L", "BME.L", "MKS.L"]

returns = master[[f"return_{t}" for t in tickers]].copy()
returns.columns = tickers

trends = master[[f"trends_{t}" for t in tickers]].copy()
trends.columns = tickers

port = master["Total_Container_Imports"].copy()

# ==============================================================
# Rebuild the composite signal (same logic as backtest.py)
# ==============================================================

window = 12

trends_z = (trends - trends.rolling(window).mean()) / trends.rolling(window).std()
port_z = (port - port.rolling(window).mean()) / port.rolling(window).std()

composite = trends_z.copy()
for t in tickers:
    composite[t] = (trends_z[t] + port_z) / 2

composite = composite.dropna()

# ==============================================================
# For each month, correlate signal cross-section with next-month returns
# ==============================================================

# Shift returns backward by 1: the return in row t is actually next month's return
forward_returns = returns.shift(-1).loc[composite.index]

# For each month, correlate that month's signal values across 7 stocks
# with next-month returns across the same 7 stocks.
# A positive correlation each month = strategy is working
monthly_ic = []
dates = []

for date in composite.index:
    sig_row = composite.loc[date]
    ret_row = forward_returns.loc[date]

    # Drop any NaN before correlating
    combined = pd.concat([sig_row, ret_row], axis=1).dropna()
    if len(combined) < 3:
        continue

    ic = combined.iloc[:, 0].corr(combined.iloc[:, 1])
    monthly_ic.append(ic)
    dates.append(date)

ic_series = pd.Series(monthly_ic, index=dates)

# ==============================================================
# Compute 12-month rolling average IC to smooth noise
# ==============================================================

rolling_ic = ic_series.rolling(12).mean()

# ==============================================================
# Print summary statistics
# ==============================================================

print("="*60)
print("SIGNAL DIAGNOSTIC")
print("="*60)
print(f"\nMonthly Information Coefficient (IC):")
print(f"  Mean IC:        {ic_series.mean():+.3f}")
print(f"  Median IC:      {ic_series.median():+.3f}")
print(f"  % months positive: {(ic_series > 0).mean():.1%}")
print(f"  Observations:   {len(ic_series)}")

# Split at Jan 2024 (the pivot point identified visually)
pre_2024 = ic_series[ic_series.index < "2024-01-01"]
post_2024 = ic_series[ic_series.index >= "2024-01-01"]

print(f"\nSubperiod comparison:")
print(f"  Pre-Jan 2024:  mean IC = {pre_2024.mean():+.3f} over {len(pre_2024)} months")
print(f"  Post-Jan 2024: mean IC = {post_2024.mean():+.3f} over {len(post_2024)} months")

# ==============================================================
# Chart: rolling IC over time with zero line
# ==============================================================

fig, ax = plt.subplots(figsize=(10, 6))

# Plot raw monthly IC as light dots
ax.plot(ic_series.index, ic_series.values, "o", alpha=0.3, markersize=4, label="Monthly IC")

# Plot smoothed rolling IC as bold line
ax.plot(rolling_ic.index, rolling_ic.values, linewidth=2.5, label="12-month rolling mean IC")

# Zero line - anything above = signal working, below = not working
ax.axhline(0, color="black", linewidth=1, linestyle="--", alpha=0.6)

# Highlight the Jan 2024 pivot
ax.axvline(pd.Timestamp("2024-01-01"), color="red", linewidth=1, linestyle=":", alpha=0.7)
ax.text(pd.Timestamp("2024-01-15"), ax.get_ylim()[1] * 0.85, "Jan 2024\npivot", color="red", fontsize=9)

ax.set_title("Signal Predictive Power Over Time\n(Cross-Sectional Correlation Between Composite Signal and Next-Month Returns)")
ax.set_xlabel("Date")
ax.set_ylabel("Information Coefficient (IC)")
ax.legend(loc="lower left")
ax.grid(alpha=0.3)
plt.tight_layout()

chart_path = "outputs/signal_diagnostic.png"
plt.savefig(chart_path, dpi=100)
print(f"\nDiagnostic chart saved to {chart_path}")