import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime

from finance_ai.config import CONFIG

class Base(DeclarativeBase):
    pass

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, index=True, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    account = Column(String)
    currency = Column(String)
    category = Column(String)
    subcategory = Column(String)
    merchant = Column(String)
    mcc = Column(String)
    tx_hash = Column(String, unique=True, index=True, nullable=False)


def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=CONFIG.db_echo, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, SessionLocal
