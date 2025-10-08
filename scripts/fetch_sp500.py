#!/usr/bin/env python3
"""
Fetch 30 years of monthly S&P 500 data and save to CSV.
Saves to: data/market/sp500_monthly.csv
Columns: Date, AdjClose, Return
Note: /data is gitignored by default in this repo. Change .gitignore if you want to commit the CSV.
"""
import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def main():
    # Determine date range: last 30 years from today
    end = datetime.today()
    start = end - timedelta(days=365 * 30 + 30)  # add pad for leap years

    ticker = "^GSPC"  # S&P 500 index

    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1mo",
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise RuntimeError("No data returned from yfinance for ^GSPC")

    # Keep Close (auto_adjust=True adjusts for splits/dividends)
    # Normalize/flatten columns to reliably detect Close/Adj Close
    if isinstance(df.columns, pd.MultiIndex):
        flat_cols = ["_".join([str(x) for x in col if str(x) != ""]) for col in df.columns]
        df.columns = flat_cols
    else:
        df.columns = [str(c) for c in df.columns]

    # Find a 'close' column, prefer 'adj close' if present
    lower_cols = [c.lower() for c in df.columns]
    close_idx = None
    for prefer in ["adj close", "adj_close", "adjusted_close", "close"]:
        for i, c in enumerate(lower_cols):
            if prefer in c:
                close_idx = i
                break
        if close_idx is not None:
            break
    if close_idx is None:
        raise RuntimeError(f"Could not locate a Close/Adj Close column in: {list(df.columns)}")
    close_col = df.columns[close_idx]
    close = df[close_col]

    df = close.rename("AdjClose").to_frame()
    df = df.rename_axis("Date").reset_index()
    df = df.sort_values("Date")

    # Compute simple returns from AdjClose
    df["Return"] = df["AdjClose"].pct_change()
    df = df.dropna().reset_index(drop=True)

    # Ensure output directory exists
    out_dir = os.path.join("data", "market")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "sp500_monthly.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
