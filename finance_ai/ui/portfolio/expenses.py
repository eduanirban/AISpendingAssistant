import streamlit as st
from .state import init_portfolio_state
from .inputs import currency_input


def render_expenses():
    init_portfolio_state()

    st.subheader("Retirement Expenses")
    st.caption("Expected annual costs in retirement (today's dollars).")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.portfolio["expenses"]["basic"] = currency_input(
            "Basic (housing, utilities, healthcare)", key="exp_basic", value=st.session_state.portfolio["expenses"]["basic"],
            help_text="Minimum lifestyle costs."
        )
        st.session_state.portfolio["expenses"]["discretionary"] = currency_input(
            "Discretionary (travel, dining, extras)", key="exp_disc", value=st.session_state.portfolio["expenses"]["discretionary"],
            help_text="Flexible spending."
        )
    with c2:
        st.session_state.portfolio["expenses"]["mortgage_payment"] = currency_input(
            "Monthly mortgage payment", key="exp_mort", value=st.session_state.portfolio["expenses"]["mortgage_payment"],
            help_text="Enter 0 if no mortgage."
        )
        st.session_state.portfolio["expenses"]["payer"] = st.selectbox(
            "Mortgage payer", options=["self", "partner", "joint"], index=["self","partner","joint"].index(st.session_state.portfolio["expenses"]["payer"]), key="exp_payer" 
        )
        st.session_state.portfolio["expenses"]["mortgage_ends_at_age"] = st.number_input(
            "Mortgage ends at age (payer)", min_value=0, max_value=110, value=int(st.session_state.portfolio["expenses"]["mortgage_ends_at_age"]), step=1,
            help="Age of the selected payer when mortgage will be fully paid", key="exp_mort_end_age"
        )

    # Summary
    annual_core = st.session_state.portfolio["expenses"]["basic"] + st.session_state.portfolio["expenses"]["discretionary"]
    mort_annual = st.session_state.portfolio["expenses"]["mortgage_payment"] * 12.0
    e1, e2, e3 = st.columns(3)
    e1.metric("Annual basic + discretionary", f"${annual_core:,.0f}")
    e2.metric("Annual mortgage", f"${mort_annual:,.0f}")
    e3.metric("Total annual (incl. mortgage)", f"${(annual_core + mort_annual):,.0f}")
