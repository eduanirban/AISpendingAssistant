import pandas as pd
from dateutil import parser as dateparser


def _parse_date(val):
    if pd.isna(val):
        return pd.NaT
    try:
        return pd.to_datetime(val)
    except Exception:
        try:
            return pd.to_datetime(dateparser.parse(str(val)))
        except Exception:
            return pd.NaT


def normalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Dates
    df['date'] = df['date'].apply(_parse_date)
    df = df[df['date'].notna()]

    # Description cleanup
    df['description'] = df['description'].astype(str).str.strip()

    # Amount to float
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df = df[df['amount'].notna()]

    # Transaction direction
    # If type hints exist, keep as-is; else infer: negative = debit, positive = credit
    if 'type' not in df.columns:
        df['type'] = df['amount'].apply(lambda x: 'debit' if x < 0 else 'credit')
    else:
        df['type'] = df['type'].astype(str).str.lower()

    # Account and currency optional
    for col in ['account', 'currency']:
        if col not in df.columns:
            df[col] = None

    # Standard columns
    for col in ['category', 'subcategory', 'merchant', 'mcc']:
        if col not in df.columns:
            df[col] = None

    return df[['date','description','amount','type','account','currency','category','subcategory','merchant','mcc']]
