import streamlit as st
from .state import init_portfolio_state


def render_social_pension():
    init_portfolio_state()

    st.subheader("Social Security & Pension")
    st.caption("Enter annual amounts (today's dollars) and start ages for each spouse.")

    for who in ["self", "partner"]:
        with st.expander(f"{'You' if who=='self' else 'Partner'}", expanded=(who == "self")):
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.portfolio["income"][who]["ss"] = st.number_input(
                    "Social Security (annual)", min_value=0.0,
                    value=float(st.session_state.portfolio["income"][who]["ss"]), step=1000.0, format="%.2f",
                    key=f"sp_{who}_ss_amt",
                )
                st.session_state.portfolio["income"][who]["pension"] = st.number_input(
                    "Pension (annual)", min_value=0.0,
                    value=float(st.session_state.portfolio["income"][who]["pension"]), step=1000.0, format="%.2f",
                    key=f"sp_{who}_pension_amt",
                )
            with c2:
                st.session_state.portfolio["income"][who]["ss_start_age"] = st.number_input(
                    "SS start age", min_value=0, max_value=110,
                    value=int(st.session_state.portfolio["income"][who]["ss_start_age"]), step=1,
                    key=f"sp_{who}_ss_start",
                )
                st.session_state.portfolio["income"][who]["pension_start_age"] = st.number_input(
                    "Pension start age", min_value=0, max_value=110,
                    value=int(st.session_state.portfolio["income"][who]["pension_start_age"]), step=1,
                    key=f"sp_{who}_pension_start",
                )
