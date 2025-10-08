import os
import numpy as np
import pandas as pd
import streamlit as st

from finance_ai.intelligence.monte_carlo import (
    MCConfig,
    load_monthly_returns,
    simulate_paths,
    simulate_paths_two_asset,
)
from .state import init_portfolio_state


def _sum_accounts(side: str) -> float:
    a = st.session_state.portfolio["accounts"][side]
    return float(a["401k"]) + float(a["traditional_ira"]) + float(a["roth_ira"]) + float(a["brokerage"]) 


essential_info = """
This simulation bootstraps monthly S&P 500 returns from the last ~30 years (local CSV).
Spending grows by inflation monthly. Pre-retirement contributions are not yet modeled (coming next).
Results show survival probability and percentile bands of portfolio value.
"""


def render_simulation():
    init_portfolio_state()

    st.subheader("Monte Carlo Simulation")
    st.caption("Project how long your portfolio lasts under market uncertainty.")
    st.info(essential_info)

    # Inputs
    c1, c2, c3 = st.columns(3)
    with c1:
        n_sims = st.number_input("Number of simulations", min_value=500, max_value=20000, value=1000, step=500, key="mc_n_sims")
        annual_infl = st.number_input("Annual inflation %", min_value=0.0, max_value=10.0, value=2.4, step=0.1, key="mc_infl") / 100.0
    with c2:
        data_path = st.text_input("Equity returns CSV (S&P 500)", value=os.path.join("data", "market", "sp500_monthly.csv"), key="mc_csv")
        seed = st.number_input("Random seed (optional)", min_value=0, max_value=10_000, value=42, step=1, key="mc_seed")
    with c3:
        run_btn = st.button("Run Simulation", type="primary", use_container_width=True)

    # Allocation and bond data
    st.markdown("---")
    a1, a2, a3 = st.columns([1,1,1])
    with a1:
        stock_weight = st.slider("Equity allocation (%)", min_value=0, max_value=100, value=60, step=5, key="mc_stock_w") / 100.0
    with a2:
        bond_csv = st.text_input("Bond returns CSV (AGG/BND)", value=os.path.join("data", "market", "bond_monthly.csv"), key="mc_bond_csv")
    with a3:
        annual_rebalance = st.checkbox("Annual rebalance", value=True, key="mc_rebalance")

    # Derive household parameters
    self_age = st.session_state.portfolio["user"]["self"]["age"]
    partner_age = st.session_state.portfolio["user"]["partner"]["age"]
    self_ret_age = st.session_state.portfolio["user"]["self"]["retirement_age"]
    partner_ret_age = st.session_state.portfolio["user"]["partner"]["retirement_age"]
    self_le = st.session_state.portfolio["user"]["self"]["life_expectancy"]
    partner_le = st.session_state.portfolio["user"]["partner"]["life_expectancy"]

    # Horizon to joint life expectancy (max of both horizons from today)
    years_horizon = max(self_le - self_age, partner_le - partner_age)
    years_until_ret = max(min(self_ret_age - self_age, partner_ret_age - partner_age), 0)

    # Expenses
    basic = float(st.session_state.portfolio["expenses"]["basic"])  # annual in today's dollars
    disc = float(st.session_state.portfolio["expenses"]["discretionary"])  # annual
    monthly_spend_now = (basic + disc) / 12.0

    mort = float(st.session_state.portfolio["expenses"]["mortgage_payment"])  # monthly
    payer = st.session_state.portfolio["expenses"]["payer"]
    mort_end_age = int(st.session_state.portfolio["expenses"]["mortgage_ends_at_age"])  # payer age when ends
    if payer == "self":
        years_until_mort_end = max(mort_end_age - self_age, 0)
    elif payer == "partner":
        years_until_mort_end = max(mort_end_age - partner_age, 0)
    else:  # joint -> use max
        years_until_mort_end = max(mort_end_age - min(self_age, partner_age), 0)

    # Initial balances
    initial_balance = _sum_accounts("self") + _sum_accounts("partner")

    # Run
    if run_btn:
        try:
            rets = load_monthly_returns(data_path)
        except Exception as e:
            st.error(f"Failed to load returns CSV: {e}")
            return

        cfg = MCConfig(
            n_sims=int(n_sims),
            monthly_inflation=(1 + annual_infl) ** (1 / 12.0) - 1.0,
            seed=int(seed),
        )

        # Try two-asset if bond CSV loads; else fallback to equity-only
        use_two_asset = False
        try:
            bond_rets = load_monthly_returns(bond_csv)
            use_two_asset = True
        except Exception:
            use_two_asset = False

        if use_two_asset:
            balances, alive = simulate_paths_two_asset(
                initial_balance=initial_balance,
                stock_returns=rets,
                bond_returns=bond_rets,
                years_horizon=int(years_horizon),
                years_until_retirement=int(years_until_ret),
                monthly_spend_now=monthly_spend_now,
                monthly_mortgage_now=mort,
                years_until_mortgage_end=int(years_until_mort_end),
                stock_weight=float(stock_weight),
                annual_rebalance=bool(annual_rebalance),
                cfg=cfg,
            )
        else:
            balances, alive = simulate_paths(
                initial_balance=initial_balance,
                ret_series=rets,
                years_horizon=int(years_horizon),
                years_until_retirement=int(years_until_ret),
                monthly_spend_now=monthly_spend_now,
                monthly_mortgage_now=mort,
                years_until_mortgage_end=int(years_until_mort_end),
                cfg=cfg,
            )

        T = balances.shape[1]
        months = np.arange(T)
        # Percentiles
        p10 = np.percentile(balances, 10, axis=0)
        p50 = np.percentile(balances, 50, axis=0)
        p90 = np.percentile(balances, 90, axis=0)
        survival = alive.cummin(axis=1)[:, -1].mean()  # proportion alive at final month

        st.success(f"Survival to joint life horizon: {survival*100:.1f}%")

        # Plot bands
        try:
            import altair as alt
            chart_df = pd.DataFrame({
                "month": months,
                "p10": p10,
                "p50": p50,
                "p90": p90,
            })
            base = alt.Chart(chart_df).encode(x="month")
            band = base.mark_area(opacity=0.2, color="#1c7ed6").encode(y="p10", y2="p90")
            med = base.mark_line(color="#1c7ed6").encode(y="p50")
            st.altair_chart(band + med, use_container_width=True)
        except Exception:
            st.line_chart(pd.DataFrame({"p10": p10, "p50": p50, "p90": p90}), height=300)

        # Table snapshot
        st.subheader("Percentiles Table (annual checkpoints)")
        years = np.arange(0, int(np.ceil(T / 12)))
        rows = []
        for y in years:
            idx = min(T - 1, y * 12)
            rows.append({
                "Year": y,
                "p10": p10[idx],
                "p50": p50[idx],
                "p90": p90[idx],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=300)
