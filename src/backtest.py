"""
Backtest a simple long-only monthly rebalanced strategy on UK consumer stocks.

Strategy logic:
- Each month, compute three signals per stock:
    1. Trends z-score: is search interest unusually high vs 12-month history?
    2. Port freight z-score: is UK import activity unusually high? (macro)
    3. ONS retail sales z-score: is the stock's category showing unusually
       strong YoY growth? (stock-specific via category mapping)
- Combine into a composite score (equal weighted across three signals)
- Hold the top 3 ranked stocks equal-weighted for the next month
- Rebalance at month-end

ONS data is lagged by 1 month in the master dataset to respect the
real-world publication lag (avoids lookahead bias).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# ==============================================================
# Load the master dataset
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

ons = master[[f"ons_{t}" for t in tickers]].copy()
ons.columns = tickers

# ==============================================================
# Build signals: 12-month rolling z-scores
# ==============================================================

window = 12

# Signal 1: Google Trends attention z-score (stock-specific)
trends_z = (trends - trends.rolling(window).mean()) / trends.rolling(window).std()

# Signal 2: Port freight z-score (macro, applied to all stocks)
port_mean = port.rolling(window).mean()
port_std = port.rolling(window).std()
port_z = (port - port_mean) / port_std

# Signal 3: ONS retail sales z-score (category-mapped per stock)
ons_z = (ons - ons.rolling(window).mean()) / ons.rolling(window).std()

# Composite: equal-weight average of the three
composite = trends_z.copy()
for t in tickers:
    composite[t] = (trends_z[t] + port_z + ons_z[t]) / 3

composite = composite.dropna()

# ==============================================================
# Generate positions: top 3 stocks each month
# ==============================================================

positions = pd.DataFrame(index=composite.index, columns=tickers, data=0.0)

n_hold = 3

for date in composite.index:
    scores = composite.loc[date]
    top_n = scores.nlargest(n_hold).index
    for t in top_n:
        positions.loc[date, t] = 1.0 / n_hold

# ==============================================================
# Compute strategy returns
# ==============================================================

positions_lagged = positions.shift(1).fillna(0)
returns_aligned = returns.loc[positions_lagged.index]

strategy_returns = (positions_lagged * returns_aligned).sum(axis=1)

tc_per_month = 0.0020
strategy_returns_net = strategy_returns - tc_per_month

# ==============================================================
# Benchmark: equal-weight buy-and-hold
# ==============================================================

benchmark_returns = returns_aligned.mean(axis=1)

# ==============================================================
# Performance metrics
# ==============================================================

def sharpe(returns_series, periods_per_year=12):
    mean = returns_series.mean() * periods_per_year
    vol = returns_series.std() * np.sqrt(periods_per_year)
    return mean / vol if vol > 0 else 0

def max_drawdown(returns_series):
    cum = (1 + returns_series).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum - running_max) / running_max
    return drawdown.min()

def annualised_return(returns_series, periods_per_year=12):
    cum = (1 + returns_series).prod()
    n_years = len(returns_series) / periods_per_year
    return cum ** (1 / n_years) - 1

print("="*60)
print("BACKTEST RESULTS - Three-Signal Composite")
print("="*60)
print(f"Signals: Google Trends + Port Freight + ONS Retail Sales")
print(f"Period: {strategy_returns.index[0].date()} to {strategy_returns.index[-1].date()}")
print(f"Months in sample: {len(strategy_returns)}")
print(f"\n{'Metric':<25} {'Strategy':<12} {'Benchmark':<12}")
print("-" * 50)
print(f"{'Annualised return':<25} {annualised_return(strategy_returns_net):>10.2%}  {annualised_return(benchmark_returns):>10.2%}")
print(f"{'Annualised volatility':<25} {strategy_returns_net.std() * np.sqrt(12):>10.2%}  {benchmark_returns.std() * np.sqrt(12):>10.2%}")
print(f"{'Sharpe ratio':<25} {sharpe(strategy_returns_net):>10.2f}  {sharpe(benchmark_returns):>10.2f}")
print(f"{'Max drawdown':<25} {max_drawdown(strategy_returns_net):>10.2%}  {max_drawdown(benchmark_returns):>10.2%}")
print(f"{'Hit rate':<25} {(strategy_returns_net > 0).mean():>10.2%}  {(benchmark_returns > 0).mean():>10.2%}")
print(f"\nTransaction costs: 20bps per month (applied to strategy only)")

# ==============================================================
# Equity curve chart
# ==============================================================

os.makedirs("outputs", exist_ok=True)

fig, ax = plt.subplots(figsize=(10, 6))
(1 + strategy_returns_net).cumprod().plot(ax=ax, label="Strategy (net of costs)", linewidth=2)
(1 + benchmark_returns).cumprod().plot(ax=ax, label="Equal-weight benchmark", linewidth=2, linestyle="--")
ax.set_title("Cumulative Returns: Three-Signal Alt-Data Strategy vs Benchmark")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative return (starting value = 1)")
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()

chart_path = "outputs/equity_curve.png"
plt.savefig(chart_path, dpi=100)
print(f"\nEquity curve saved to {chart_path}")

strategy_returns_net.to_csv("outputs/strategy_returns.csv", header=["strategy_return"])
print(f"Strategy returns saved to outputs/strategy_returns.csv")