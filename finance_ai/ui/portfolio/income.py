import streamlit as st
from .state import init_portfolio_state


def render_income():
    init_portfolio_state()

    st.subheader("Household Income")
    st.caption("Annual pre-tax income sources for each spouse.")
    for who in ["self", "partner"]:
        with st.expander(f"{'You' if who=='self' else 'Partner'} Income", expanded=(who == "self")):
            c1, c2, c3 = st.columns(3)
            st.session_state.portfolio["income"][who]["salary"] = c1.number_input(
                "Salary", min_value=0.0, value=float(st.session_state.portfolio["income"][who]["salary"]), step=1000.0, format="%.2f",
                help="Annual W-2 or self-employment income", key=f"inc_{who}_salary"
            )
            st.session_state.portfolio["income"][who]["rental"] = c2.number_input(
                "Rental income", min_value=0.0, value=float(st.session_state.portfolio["income"][who]["rental"]), step=500.0, format="%.2f",
                help="Net annual rental income", key=f"inc_{who}_rental"
            )
            st.session_state.portfolio["income"][who]["pension"] = c3.number_input(
                "Pension", min_value=0.0, value=float(st.session_state.portfolio["income"][who]["pension"]), step=500.0, format="%.2f",
                help="Annual pension income (once in pay)", key=f"inc_{who}_pension"
            )

    # Summary
    total_self = sum(st.session_state.portfolio["income"]["self"].values())
    total_partner = sum(st.session_state.portfolio["income"]["partner"].values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Your annual income", f"${total_self:,.0f}")
    m2.metric("Partner annual income", f"${total_partner:,.0f}")
    m3.metric("Household income", f"${(total_self + total_partner):,.0f}")
