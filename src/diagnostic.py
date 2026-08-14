"""
Diagnostic: information coefficient over time for each individual
stock-selection signal AND the composite.

Note on Port Freight: this is a macro (market-timing) signal - it takes
the same value across all stocks in any given month. It cannot generate
cross-sectional IC by construction (you cannot rank 7 stocks by an
identical value). It is excluded from the per-signal IC analysis below
but retained in the composite for market-timing exposure.

Cross-sectional IC = correlation between signal values and next-month
returns across the 7 stocks in each month. Positive IC = signal works.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings

# Suppress the divide warnings from correlations of constant series
warnings.filterwarnings("ignore", category=RuntimeWarning)

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

ons = master[[f"ons_{t}" for t in tickers]].copy()
ons.columns = tickers

# Build signals
window = 12
trends_z = (trends - trends.rolling(window).mean()) / trends.rolling(window).std()
port_z_series = (port - port.rolling(window).mean()) / port.rolling(window).std()
ons_z = (ons - ons.rolling(window).mean()) / ons.rolling(window).std()

# Composite: equal-weight of three signals (port broadcast to all stocks)
composite = pd.DataFrame(index=trends_z.index, columns=tickers)
for t in tickers:
    composite[t] = (trends_z[t] + port_z_series + ons_z[t]) / 3

trends_z = trends_z.dropna()
ons_z = ons_z.dropna()
composite = composite.dropna()

def compute_monthly_ic(signal_df, returns_df):
    forward_returns = returns_df.shift(-1).loc[signal_df.index]
    ics = []
    dates = []
    for date in signal_df.index:
        sig_row = signal_df.loc[date]
        ret_row = forward_returns.loc[date]
        combined = pd.concat([sig_row, ret_row], axis=1).dropna()
        if len(combined) < 3:
            continue
        ic = combined.iloc[:, 0].corr(combined.iloc[:, 1])
        ics.append(ic)
        dates.append(date)
    return pd.Series(ics, index=dates)

ic_trends = compute_monthly_ic(trends_z, returns)
ic_ons = compute_monthly_ic(ons_z, returns)
ic_composite = compute_monthly_ic(composite, returns)

print("="*60)
print("SIGNAL DIAGNOSTIC - Cross-Sectional Information Coefficient")
print("="*60)
print("\nNote: Port Freight excluded (macro signal, no cross-sectional variation)")

def summarise(name, ic):
    print(f"\n{name}:")
    print(f"  Mean IC:              {ic.mean():+.3f}")
    print(f"  Median IC:            {ic.median():+.3f}")
    print(f"  % months positive:    {(ic > 0).mean():.1%}")
    print(f"  Observations:         {len(ic)}")
    pre = ic[ic.index < "2024-01-01"]
    post = ic[ic.index >= "2024-01-01"]
    print(f"  Pre-Jan 2024 mean:    {pre.mean():+.3f} ({len(pre)} months)")
    print(f"  Post-Jan 2024 mean:   {post.mean():+.3f} ({len(post)} months)")

summarise("Google Trends", ic_trends)
summarise("ONS Retail Sales", ic_ons)
summarise("Composite (Trends + Port + ONS)", ic_composite)

# Chart
fig, ax = plt.subplots(figsize=(11, 7))

for name, ic, color in [
    ("Google Trends", ic_trends, "tab:blue"),
    ("ONS Retail Sales", ic_ons, "tab:orange"),
    ("Composite (3-signal)", ic_composite, "tab:red"),
]:
    rolling = ic.rolling(12).mean()
    ax.plot(rolling.index, rolling.values, linewidth=2, label=name, color=color)

ax.axhline(0, color="black", linewidth=1, linestyle="--", alpha=0.6)
ax.axvline(pd.Timestamp("2024-01-01"), color="grey", linewidth=1, linestyle=":", alpha=0.7)
ax.text(pd.Timestamp("2024-01-15"), 0.15, "Jan 2024\nregime shift", color="grey", fontsize=9)

ax.set_title("Cross-Sectional Signal Predictive Power\n(12-Month Rolling Mean Information Coefficient)")
ax.set_xlabel("Date")
ax.set_ylabel("Rolling 12-month mean IC")
ax.legend(loc="lower left", framealpha=0.9)
ax.grid(alpha=0.3)
plt.tight_layout()

chart_path = "outputs/signal_diagnostic.png"
plt.savefig(chart_path, dpi=100)
print(f"\nDiagnostic chart saved to {chart_path}")