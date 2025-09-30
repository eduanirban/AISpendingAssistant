import hashlib
import pandas as pd


def _row_hash(row) -> str:
    # Stable hash on date (YYYY-MM-DD), amount (rounded 0.01), and description
    date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d') if pd.notna(row['date']) else ''
    amt = round(float(row['amount']), 2) if pd.notna(row['amount']) else 0.0
    desc = (row.get('description') or '').strip().lower()
    payload = f"{date_str}|{amt:.2f}|{desc}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def compute_hashes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['tx_hash'] = df.apply(_row_hash, axis=1)
    return df


def filter_new_transactions(df: pd.DataFrame, existing_hashes: set) -> pd.DataFrame:
    return df[~df['tx_hash'].isin(existing_hashes)].copy()
