from typing import Optional, Iterable
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .db import Transaction

class TransactionRepository:
    def __init__(self, engine, SessionLocal):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def get_existing_hashes(self) -> Iterable[str]:
        with self.SessionLocal() as session:
            rows = session.execute(select(Transaction.tx_hash)).all()
            return [r[0] for r in rows]

    def insert_transactions(self, df: pd.DataFrame) -> int:
        records = df.to_dict(orient='records')
        objs = [Transaction(**{
            'date': r['date'],
            'description': r['description'],
            'amount': float(r['amount']),
            'type': r['type'],
            'account': r.get('account'),
            'currency': r.get('currency'),
            'category': r.get('category'),
            'subcategory': r.get('subcategory'),
            'merchant': r.get('merchant'),
            'mcc': r.get('mcc'),
            'tx_hash': r['tx_hash'],
        }) for r in records]
        with self.SessionLocal() as session:
            session: Session
            session.add_all(objs)
            session.commit()
            return len(objs)

    def fetch_transactions(self, start_date, end_date, category_contains: str = "") -> pd.DataFrame:
        with self.SessionLocal() as session:
            stmt = select(Transaction).where(Transaction.date >= start_date, Transaction.date <= end_date)
            if category_contains:
                like = f"%{category_contains.lower()}%"
                stmt = stmt.where(func.lower(Transaction.category).like(like))
            rows = session.execute(stmt).scalars().all()
        data = [{
            'date': r.date,
            'description': r.description,
            'amount': r.amount,
            'type': r.type,
            'account': r.account,
            'currency': r.currency,
            'category': r.category,
            'subcategory': r.subcategory,
            'merchant': r.merchant,
            'mcc': r.mcc,
            'tx_hash': r.tx_hash,
        } for r in rows]
        return pd.DataFrame(data)
