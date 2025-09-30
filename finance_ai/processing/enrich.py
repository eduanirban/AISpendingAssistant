import pandas as pd

MERCHANT_NORMALIZATION = [
    ("starbucks", "Starbucks"),
    ("amazon", "Amazon"),
    ("ubereats", "Uber Eats"),
    ("uber", "Uber"),
    ("lyft", "Lyft"),
]

MCC_RULES = [
    ("coffee", "5814"),
    ("starbucks", "5814"),
    ("grocery", "5411"),
    ("amazon", "5310"),
    ("uber", "4121"),
]


def enrich_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Merchant normalization (very simple; replace with embeddings later)
    desc_lower = df['description'].str.lower()
    merchant = []
    for text in desc_lower:
        label = None
        for key, norm in MERCHANT_NORMALIZATION:
            if key in text:
                label = norm
                break
        merchant.append(label)
    df['merchant'] = merchant

    # MCC guess by keyword
    mcc = []
    for text in desc_lower:
        code = None
        for key, code_guess in MCC_RULES:
            if key in text:
                code = code_guess
                break
        mcc.append(code)
    df['mcc'] = mcc

    return df
