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
                "self": {
                    "salary": 0.0,
                    "rental": 0.0,
                    "rental_start_age": 0,  # 0 means start now
                    "rental_end_age": 0,    # 0 means no end
                    "pension": 0.0,
                    "pension_start_age": 0,
                    "ss": 0.0,  # Social Security annual amount
                    "ss_start_age": 0,
                },
                "partner": {
                    "salary": 0.0,
                    "rental": 0.0,
                    "rental_start_age": 0,
                    "rental_end_age": 0,
                    "pension": 0.0,
                    "pension_start_age": 0,
                    "ss": 0.0,
                    "ss_start_age": 0,
                },
            },
            "expenses": {
                "basic": 0.0,
                "discretionary": 0.0,
                "mortgage_payment": 0.0,
                "mortgage_ends_at_age": 0,
                "payer": "self",
            },
            "policy": {
                # Allocation & Rebalancing
                "stock_weight": 0.60,
                "annual_rebalance": True,
                # Contributions (household, pre-retirement)
                "monthly_contrib": 0.0,
                "annual_contrib_growth": 0.0,  # 0.03 => 3%
                "contrib_target": "traditional",  # traditional|roth|taxable
                # Taxes & withdrawal order
                "use_taxed": True,
                "ordinary_tax": 0.22,
                "capg_tax": 0.15,
            },
        }
        # Windfalls: list of {label, amount, age}
        st.session_state["portfolio"].setdefault("windfalls", [])
