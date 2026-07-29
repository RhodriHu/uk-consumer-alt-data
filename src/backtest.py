"""
Backtest a simple long-only monthly rebalanced strategy on UK consumer stocks.

Strategy logic:
- Each month, compute two signals per stock:
    1. Trends z-score: is search interest unusually high vs 12-month history?
    2. Port freight z-score: is UK import activity unusually high?
- Combine into a composite score (equal weighted)
- Hold the top 3 ranked stocks equal-weighted for the next month
- Rebalance at month-end

The port freight signal is a macro tilt (same value applied to all stocks),
while trends is stock-specific. Together they capture attention momentum
plus a UK imports backdrop.

This is deliberately simple. Interview-defensible framing:
"I wanted to test whether combining stock-specific attention data with
macro import activity produces a signal that beats naive equal-weight,
not to build a production system."
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

# Separate return columns and trends columns
returns = master[[f"return_{t}" for t in tickers]].copy()
returns.columns = tickers  # simpler names

trends = master[[f"trends_{t}" for t in tickers]].copy()
trends.columns = tickers

port = master["Total_Container_Imports"].copy()

# ==============================================================
# Build signals: 12-month rolling z-scores
# ==============================================================

# Rolling window length (in months) for computing z-scores
window = 12

# Trends z-score: is search interest unusually high this month
# vs the trailing 12-month average for the same stock?
trends_mean = trends.rolling(window).mean()
trends_std = trends.rolling(window).std()
trends_z = (trends - trends_mean) / trends_std

# Port freight z-score: is UK inbound tonnage unusually high?
# Same value applied across all stocks (macro tilt)
port_mean = port.rolling(window).mean()
port_std = port.rolling(window).std()
port_z = (port - port_mean) / port_std

# Composite score: average the two z-scores
# Because port_z is a single number per month, we broadcast it across all tickers
composite = trends_z.copy()
for t in tickers:
    composite[t] = (trends_z[t] + port_z) / 2

# Drop the first 12 months where rolling stats aren't defined
composite = composite.dropna()

# ==============================================================
# Generate positions: top 3 stocks each month
# ==============================================================

# For each month, rank stocks by composite score; top 3 get equal weight
positions = pd.DataFrame(index=composite.index, columns=tickers, data=0.0)

n_hold = 3  # hold the top 3 ranked stocks each month

for date in composite.index:
    scores = composite.loc[date]
    # Get the tickers of the top N by score
    top_n = scores.nlargest(n_hold).index
    # Equal weight across held stocks
    for t in top_n:
        positions.loc[date, t] = 1.0 / n_hold

# ==============================================================
# Compute strategy returns
# ==============================================================

# Position at end of month M determines return during month M+1
# So we shift positions by 1 to avoid using future information
positions_lagged = positions.shift(1).fillna(0)

# Strategy return each month = sum of (position weight * stock return)
# Align returns to same dates as positions
returns_aligned = returns.loc[positions_lagged.index]

# Element-wise multiply and sum across stocks
strategy_returns = (positions_lagged * returns_aligned).sum(axis=1)

# Transaction costs: assume 10bps per side each time we rebalance
# For simplicity, subtract 20bps from every month's return (approximation)
tc_per_month = 0.0020
strategy_returns_net = strategy_returns - tc_per_month

# ==============================================================
# Benchmark: equal-weight buy-and-hold across all 7 stocks
# ==============================================================

benchmark_returns = returns_aligned.mean(axis=1)

# ==============================================================
# Performance metrics
# ==============================================================

def sharpe(returns_series, periods_per_year=12):
    """Annualised Sharpe ratio, assuming zero risk-free rate."""
    mean = returns_series.mean() * periods_per_year
    vol = returns_series.std() * np.sqrt(periods_per_year)
    return mean / vol if vol > 0 else 0

def max_drawdown(returns_series):
    """Maximum peak-to-trough decline in cumulative returns."""
    cum = (1 + returns_series).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum - running_max) / running_max
    return drawdown.min()

def annualised_return(returns_series, periods_per_year=12):
    """Geometric annualised return."""
    cum = (1 + returns_series).prod()
    n_years = len(returns_series) / periods_per_year
    return cum ** (1 / n_years) - 1

# Compute all metrics
print("="*60)
print("BACKTEST RESULTS")
print("="*60)
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
# Save the equity curve chart
# ==============================================================

os.makedirs("outputs", exist_ok=True)

fig, ax = plt.subplots(figsize=(10, 6))
(1 + strategy_returns_net).cumprod().plot(ax=ax, label="Strategy (net of costs)", linewidth=2)
(1 + benchmark_returns).cumprod().plot(ax=ax, label="Equal-weight benchmark", linewidth=2, linestyle="--")
ax.set_title("Cumulative Returns: Alt-Data Strategy vs Equal-Weight Benchmark")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative return (starting value = 1)")
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()

chart_path = "outputs/equity_curve.png"
plt.savefig(chart_path, dpi=100)
print(f"\nEquity curve saved to {chart_path}")

# Save strategy returns to CSV so someone can inspect
strategy_returns_net.to_csv("outputs/strategy_returns.csv", header=["strategy_return"])
print(f"Strategy returns saved to outputs/strategy_returns.csv")