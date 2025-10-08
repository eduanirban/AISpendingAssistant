#!/usr/bin/env python3
"""
Fetch ~20+ years of monthly US Aggregate Bond proxy (AGG) and save to CSV.
Saves to: data/market/bond_monthly.csv
Columns: Date, AdjClose, Return
Note: /data is gitignored by default in this repo.
"""
import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def main():
    # Try last 30 years; AGG inception is ~2003, so we'll get what's available
    end = datetime.today()
    start = end - timedelta(days=365 * 30 + 30)

    ticker = "AGG"  # iShares Core US Aggregate Bond ETF

    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1mo",
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise RuntimeError("No data returned from yfinance for AGG")

    # Normalize columns and select Close/Adj Close
    if isinstance(df.columns, pd.MultiIndex):
        flat_cols = ["_".join([str(x) for x in col if str(x) != ""]) for col in df.columns]
        df.columns = flat_cols
    else:
        df.columns = [str(c) for c in df.columns]

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

    # Monthly returns
    df["Return"] = df["AdjClose"].pct_change()
    df = df.dropna().reset_index(drop=True)

    out_dir = os.path.join("data", "market")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "bond_monthly.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
