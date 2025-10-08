import streamlit as st
from .state import init_portfolio_state


def render_current_portfolios():
    init_portfolio_state()

    st.subheader("Account Balances")
    st.caption("Enter current balances for tax-advantaged and taxable accounts.")

    for who in ["self", "partner"]:
        st.markdown(f"**{'You' if who=='self' else 'Partner'} Accounts**")
        c401, cira, croth, cbro = st.columns(4)
        st.session_state.portfolio["accounts"][who]["401k"] = c401.number_input(
            "401(k)", min_value=0.0, value=float(st.session_state.portfolio["accounts"][who]["401k"]), step=1000.0, format="%.2f",
            help="Total current balance in 401(k)", key=f"acct_{who}_401k"
        )
        st.session_state.portfolio["accounts"][who]["traditional_ira"] = cira.number_input(
            "Traditional IRA", min_value=0.0, value=float(st.session_state.portfolio["accounts"][who]["traditional_ira"]), step=1000.0, format="%.2f",
            help="Total current balance in Traditional IRA", key=f"acct_{who}_trad_ira"
        )
        st.session_state.portfolio["accounts"][who]["roth_ira"] = croth.number_input(
            "Roth IRA", min_value=0.0, value=float(st.session_state.portfolio["accounts"][who]["roth_ira"]), step=1000.0, format="%.2f",
            help="Total current balance in Roth IRA", key=f"acct_{who}_roth_ira"
        )
        st.session_state.portfolio["accounts"][who]["brokerage"] = cbro.number_input(
            "Brokerage", min_value=0.0, value=float(st.session_state.portfolio["accounts"][who]["brokerage"]), step=1000.0, format="%.2f",
            help="Total current balance in taxable brokerage", key=f"acct_{who}_brokerage"
        )

    # Summary row
    s1, s2 = st.columns(2)

    def _sum_accounts(side: str) -> float:
        a = st.session_state.portfolio["accounts"][side]
        return a["401k"] + a["traditional_ira"] + a["roth_ira"] + a["brokerage"]

    s1.metric("Your total investable assets", f"${_sum_accounts('self'):,.0f}")
    s2.metric("Partner total investable assets", f"${_sum_accounts('partner'):,.0f}")
