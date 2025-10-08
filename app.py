import os
import streamlit as st
import pandas as pd
from datetime import datetime

from finance_ai.storage.db import init_db
from finance_ai.storage.repository import TransactionRepository
from finance_ai.ingestion.parser_csv import parse_csv
from finance_ai.ingestion.parser_ofx import parse_ofx
from finance_ai.processing.normalize import normalize_transactions
from finance_ai.processing.dedupe import compute_hashes, filter_new_transactions
from finance_ai.processing.enrich import enrich_transactions
from finance_ai.intelligence.categorizer import categorize_transactions
from finance_ai.intelligence.insights import compute_insights
from finance_ai.intelligence.commentary import render_commentary
from finance_ai.ui.components import render_overview_cards, render_charts, render_transactions_table
from finance_ai.ui.portfolio.user_details import render_user_details
from finance_ai.ui.portfolio.portfolios import render_current_portfolios
from finance_ai.ui.portfolio.income import render_income
from finance_ai.ui.portfolio.expenses import render_expenses
from finance_ai.ui.portfolio.simulation import render_simulation
from finance_ai.ui.portfolio.social_pension import render_social_pension
from finance_ai.ui.portfolio.other_income import render_other_income
from finance_ai.ui.portfolio.policy import render_policy

st.set_page_config(page_title="Finance AI Workbook", layout="wide")

DATA_DIR = os.path.join(os.getcwd(), "data")
DB_PATH = os.path.join(DATA_DIR, "finance.db")

@st.cache_resource
def get_repo():
    os.makedirs(DATA_DIR, exist_ok=True)
    engine, SessionLocal = init_db(DB_PATH)
    return TransactionRepository(engine=engine, SessionLocal=SessionLocal)

# Left-hand navigation
nav = st.sidebar.radio("Navigate", ["Portfolio Analysis", "Spending Analyzer"], index=0)

if nav == "Portfolio Analysis":
    st.title("Portfolio Analysis")
    st.caption("Plan retirement with a clear view of ages, portfolios, income, and expenses.")

    # Sub-tabs within Portfolio Analysis (Simulation moved below tabs)
    tab_details, tab_portfolios, tab_income, tab_expenses, tab_social, tab_other_income, tab_policy = st.tabs([
        "User Details",
        "Current Portfolios",
        "Income",
        "Expenses",
        "Social & Pension",
        "Other Income",
        "Policy",
    ])

    with tab_details:
        render_user_details()
    with tab_portfolios:
        render_current_portfolios()
    with tab_income:
        render_income()
    with tab_expenses:
        render_expenses()
    with tab_social:
        render_social_pension()
    with tab_other_income:
        render_other_income()
    with tab_policy:
        render_policy()
    # Simulation section on main page (below tabs)
    st.markdown("---")
    st.header("Simulation")
    render_simulation()

else:
    st.title("Spending Analyzer")
    st.caption("Privacy-first: all data stays local. Upload CSV/OFX, get insights.")

    # Initialize repository when Spending Analyzer is active
    repo = get_repo()

    # Upload & Ingestion (moved from sidebar to main content)
    st.subheader("Upload Transactions")
    uploaded = st.file_uploader("CSV or OFX/QFX", type=["csv", "ofx", "qfx"]) 
    commit_btn = st.button("Ingest Uploaded File")

    if uploaded is not None and commit_btn:
        ext = os.path.splitext(uploaded.name)[1].lower()
        try:
            if ext == ".csv":
                df = parse_csv(uploaded)
            elif ext in (".ofx", ".qfx"):
                df = parse_ofx(uploaded)
            else:
                st.error("Unsupported file type.")
                df = None
            if df is not None and not df.empty:
                df = normalize_transactions(df)
                df = compute_hashes(df)
                existing = set(repo.get_existing_hashes())
                df_new = filter_new_transactions(df, existing)
                if df_new.empty:
                    st.info("No new transactions found (deduplicated).")
                else:
                    df_new = enrich_transactions(df_new)
                    df_new = categorize_transactions(df_new)
                    inserted = repo.insert_transactions(df_new)
                    st.success(f"Ingested {inserted} new transactions.")
            else:
                st.warning("No transactions parsed from file.")
        except Exception as e:
            st.exception(e)

    # Filters
    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Start date", value=datetime(datetime.now().year, 1, 1))
    with col2:
        end_date = st.date_input("End date", value=datetime.now().date())
    with col3:
        category_filter = st.text_input("Category contains", value="")

    # Data fetch
    df_all = repo.fetch_transactions(start_date=start_date, end_date=end_date, category_contains=category_filter)

    # Overview cards
    metrics = compute_insights(df_all)
    render_overview_cards(metrics)

    # Charts
    render_charts(df_all, metrics)

    # Commentary
    st.subheader("Insights Feed")
    for block in render_commentary(metrics):
        st.markdown(block)

    # Table
    st.subheader("Transactions")
    render_transactions_table(df_all)
