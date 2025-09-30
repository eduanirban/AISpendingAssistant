import pandas as pd

# Simple keyword rules for MVP. Extend with embeddings/ML and LLM fallback.
CATEGORY_RULES = [
    ("grocery", "Groceries"),
    ("supermarket", "Groceries"),
    ("whole foods", "Groceries"),
    ("trader joe", "Groceries"),
    ("starbucks", "Coffee"),
    ("coffee", "Coffee"),
    ("uber", "Transport"),
    ("lyft", "Transport"),
    ("gas", "Auto & Gas"),
    ("shell", "Auto & Gas"),
    ("rent", "Rent"),
    ("mortgage", "Mortgage"),
    ("netflix", "Entertainment"),
    ("spotify", "Entertainment"),
    ("amazon", "Shopping"),
    ("apple", "Shopping"),
]

SUBCATEGORY_RULES = {
    "Coffee": "Cafe",
    "Transport": "Rideshare",
}


def _rule_category(desc: str) -> str | None:
    d = desc.lower()
    for key, cat in CATEGORY_RULES:
        if key in d:
            return cat
    return None


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cats = []
    subs = []
    for _, row in df.iterrows():
        desc = row['description'] or ''
        cat = _rule_category(desc)
        if cat is None:
            # Placeholder for model/LLM fallback
            cat = 'Uncategorized'
        sub = SUBCATEGORY_RULES.get(cat)
        cats.append(cat)
        subs.append(sub)
    df['category'] = cats
    df['subcategory'] = subs
    return df
