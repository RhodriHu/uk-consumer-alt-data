import yfinance as yf
import pandas as pd

# Pull 1 month of Greggs data
ticker = "GRG.L"
data = yf.download(ticker, period="1mo")

# Show first 5 rows
print(data.head())

# Save to CSV
data.to_csv("data/raw/greggs_test.csv")
print(f"\nSaved data for {ticker} to data/raw/greggs_test.csv")