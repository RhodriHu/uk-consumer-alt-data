import yfinance as yf
import pandas as pd

# The 7 UK consumer stocks in our universe
tickers = [
    "GRG.L",   # Greggs
    "NXT.L",   # Next
    "JD.L",    # JD Sports
    "DOM.L",   # Domino's Pizza UK
    "JDW.L",   # Wetherspoons
    "BME.L",   # B&M European
    "MKS.L",   # Marks & Spencer
]

# Pull 3 years of daily data for each stock
for ticker in tickers:
    print(f"Pulling {ticker}...")
    data = yf.download(ticker, period="3y")
    
    # Save to CSV, filename based on ticker (remove the .L for cleanliness)
    filename = f"data/raw/{ticker.replace('.L', '').lower()}_prices.csv"
    data.to_csv(filename)
    print(f"  Saved {len(data)} rows to {filename}")

print("\nDone!")