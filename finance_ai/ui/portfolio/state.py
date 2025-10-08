import streamlit as st


def init_portfolio_state():
    """Initialize session state for portfolio analysis if not present."""
    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = {
            "user": {
                "self": {"age": 35, "retirement_age": 65, "life_expectancy": 90},
                "partner": {"age": 35, "retirement_age": 65, "life_expectancy": 90},
            },
            "accounts": {
                "self": {"401k": 0.0, "traditional_ira": 0.0, "roth_ira": 0.0, "brokerage": 0.0},
                "partner": {"401k": 0.0, "traditional_ira": 0.0, "roth_ira": 0.0, "brokerage": 0.0},
            },
            "income": {
                "self": {"salary": 0.0, "rental": 0.0, "pension": 0.0},
                "partner": {"salary": 0.0, "rental": 0.0, "pension": 0.0},
            },
            "expenses": {
                "basic": 0.0,
                "discretionary": 0.0,
                "mortgage_payment": 0.0,
                "mortgage_ends_at_age": 0,
                "payer": "self",
            },
        }
