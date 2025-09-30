import pandas as pd
from ofxparse import OfxParser

# Minimal OFX/QFX parser returning canonical columns

def parse_ofx(uploaded_file) -> pd.DataFrame:
    ofx = OfxParser.parse(uploaded_file)
    rows = []
    for account in ofx.accounts:
        for txn in account.statement.transactions:
            rows.append({
                'date': txn.date,
                'description': txn.memo or txn.payee or '',
                'amount': float(txn.amount),
                'type': txn.type,
                'account': getattr(account, 'account_id', None) or getattr(account, 'number', None),
                'currency': getattr(account.statement, 'currency', None)
            })
    df = pd.DataFrame(rows)
    return df
