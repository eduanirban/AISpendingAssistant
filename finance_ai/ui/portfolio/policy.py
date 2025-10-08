import streamlit as st
from .state import init_portfolio_state


def render_policy():
    init_portfolio_state()
    pol = st.session_state.portfolio.setdefault("policy", {})

    st.subheader("Policy: Allocation, Contributions, Taxes & Withdrawal Order")
    st.caption("Set portfolio allocation/rebalancing, pre‑retirement contributions, and tax/withdrawal policy.")

    # Allocation & Rebalancing
    st.markdown("#### Allocation & Rebalancing")
    c1, c2 = st.columns(2)
    with c1:
        pol["stock_weight"] = st.slider(
            "Equity allocation (%)", min_value=0, max_value=100,
            value=int((pol.get("stock_weight", 0.60) or 0.60) * 100), step=5,
            key="pol_stock_w"
        ) / 100.0
    with c2:
        pol["annual_rebalance"] = st.checkbox(
            "Annual rebalance", value=bool(pol.get("annual_rebalance", True)), key="pol_rebalance"
        )

    # Contributions
    st.markdown("#### Contributions (pre‑retirement)")
    c3, c4, c5 = st.columns(3)
    with c3:
        pol["monthly_contrib"] = st.number_input(
            "Household monthly contribution (today's $)", min_value=0.0,
            value=float(pol.get("monthly_contrib", 0.0) or 0.0), step=100.0, format="%.2f", key="pol_contrib_monthly"
        )
    with c4:
        pol["annual_contrib_growth"] = st.number_input(
            "Annual contribution growth %", min_value=0.0, max_value=20.0,
            value=float(pol.get("annual_contrib_growth", 0.0) or 0.0) * 100.0, step=0.5, key="pol_contrib_growth"
        ) / 100.0
    with c5:
        pol["contrib_target"] = st.selectbox(
            "Direct contributions to", options=["traditional", "roth", "taxable"],
            index=["traditional", "roth", "taxable"].index(pol.get("contrib_target", "traditional")),
            key="pol_contrib_target"
        )

    # Taxes & Withdrawal Order
    st.markdown("#### Taxes & Withdrawal Order")
    c6, c7, c8 = st.columns(3)
    with c6:
        pol["use_taxed"] = st.checkbox(
            "Use taxes + withdrawal order (Taxable → Traditional → Roth)",
            value=bool(pol.get("use_taxed", True)), key="pol_use_taxed"
        )
    with c7:
        pol["ordinary_tax"] = st.number_input(
            "Ordinary income tax % (Traditional)", min_value=0.0, max_value=60.0,
            value=float(pol.get("ordinary_tax", 0.22) or 0.22) * 100.0, step=1.0, key="pol_tax_ordinary"
        ) / 100.0
    with c8:
        pol["capg_tax"] = st.number_input(
            "Capital gains tax % (Taxable)", min_value=0.0, max_value=40.0,
            value=float(pol.get("capg_tax", 0.15) or 0.15) * 100.0, step=1.0, key="pol_tax_cg"
        ) / 100.0
