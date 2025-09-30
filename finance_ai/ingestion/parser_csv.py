import io
import pandas as pd

# Expected columns (flexible): date, description, amount, type, account, currency
# We'll try to infer common variants.

COLUMN_ALIASES = {
    'date': ['date', 'posted_date', 'transaction_date', 'txn_date'],
    'description': ['description', 'details', 'memo', 'narrative', 'payee'],
    'amount': ['amount', 'amt', 'value'],
    'type': ['type', 'txn_type', 'debit_credit'],
    'account': ['account', 'account_name', 'account_id'],
    'currency': ['currency', 'cur', 'ccy']
}

def _find_col(cols, aliases):
    cols_lower = {c.lower(): c for c in cols}
    for a in aliases:
        if a in cols_lower:
            return cols_lower[a]
    return None

def parse_csv(uploaded_file) -> pd.DataFrame:
    # uploaded_file is a BytesIO-like object from Streamlit
    content = uploaded_file.read()
    # Try utf-8 then fallback to latin-1
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=enc)
            break
        except Exception:
            df = None
    if df is None:
        raise ValueError("Could not parse CSV with utf-8 or latin-1.")
    if df.empty:
        return df

    # Map to canonical columns
    mapping = {}
    for key, aliases in COLUMN_ALIASES.items():
        col = _find_col(df.columns, aliases)
        if col is not None:
            mapping[col] = key
    df = df.rename(columns=mapping)

    # Ensure required columns exist
    for req in ["date", "description", "amount"]:
        if req not in df.columns:
            raise ValueError(f"CSV missing required column: {req}")

    # Keep canonical subset
    keep = [c for c in ["date", "description", "amount", "type", "account", "currency"] if c in df.columns]
    return df[keep].copy()
