import os
import numpy as np
import pandas as pd
import streamlit as st

from finance_ai.intelligence.monte_carlo import (
    MCConfig,
    load_monthly_returns,
    simulate_paths,
    simulate_paths_two_asset,
    simulate_paths_two_asset_taxed,
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
        # Use internal data paths; do not expose in UI
        data_path = os.path.join("data", "market", "sp500_monthly.csv")
        seed = st.number_input("Random seed (optional)", min_value=0, max_value=10_000, value=42, step=1, key="mc_seed")
    with c3:
        run_btn = st.button("Run Simulation", type="primary", use_container_width=True)

    # Internal data paths
    bond_csv = os.path.join("data", "market", "bond_monthly.csv")

    # Read policy from session state (set via Policy tab)
    pol = st.session_state.portfolio.get("policy", {})
    stock_weight = float(pol.get("stock_weight", 0.60))
    annual_rebalance = bool(pol.get("annual_rebalance", True))
    monthly_contrib = float(pol.get("monthly_contrib", 0.0))
    annual_contrib_growth = float(pol.get("annual_contrib_growth", 0.0))
    contrib_target = str(pol.get("contrib_target", "traditional"))
    use_taxed = bool(pol.get("use_taxed", True))
    ordinary_tax = float(pol.get("ordinary_tax", 0.22))
    capg_tax = float(pol.get("capg_tax", 0.15))

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
    # Split into buckets for taxed model
    def _acct_sum(key: str) -> float:
        a_self = st.session_state.portfolio["accounts"]["self"].get(key, 0.0) or 0.0
        a_partner = st.session_state.portfolio["accounts"]["partner"].get(key, 0.0) or 0.0
        return float(a_self) + float(a_partner)
    init_taxable = _acct_sum("brokerage")
    init_trad = _acct_sum("401k") + _acct_sum("traditional_ira")
    init_roth = _acct_sum("roth_ira")

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
            monthly_contribution_now=float(monthly_contrib),
            annual_contribution_growth=float(annual_contrib_growth),
        )

        # Try two-asset if bond CSV loads; else fallback to equity-only
        use_two_asset = False
        try:
            bond_rets = load_monthly_returns(bond_csv)
            use_two_asset = True
        except Exception:
            use_two_asset = False

        # Build monthly income series from SS, Pension, Rental, Windfalls
        def build_income_series(T: int) -> np.ndarray:
            inc = np.zeros(T, dtype=float)

            def add_stream(start_m: int, end_m: int | None, monthly_amt: float):
                s = max(0, start_m)
                e = T if end_m is None or end_m <= 0 else min(T, end_m)
                if monthly_amt <= 0 or s >= T:
                    return
                inc[s:e] += monthly_amt

            # Helper: months until a given age for a person
            def months_until(age_now: int, target_age: int) -> int:
                return max(0, int((target_age - age_now) * 12))

            # Social Security & Pension per spouse (annual -> monthly)
            for who, age_now in [("self", self_age), ("partner", partner_age)]:
                i = st.session_state.portfolio["income"][who]
                # Social Security
                ss_amt = float(i.get("ss", 0.0)) / 12.0
                ss_start = int(i.get("ss_start_age", 0))
                if ss_amt > 0 and ss_start > 0:
                    add_stream(months_until(age_now, ss_start), None, ss_amt)
                # Pension
                pen_amt = float(i.get("pension", 0.0)) / 12.0
                pen_start = int(i.get("pension_start_age", 0))
                if pen_amt > 0 and pen_start > 0:
                    add_stream(months_until(age_now, pen_start), None, pen_amt)
                # Rental window
                rent_amt = float(i.get("rental", 0.0)) / 12.0
                r_start_age = int(i.get("rental_start_age", 0))
                r_end_age = int(i.get("rental_end_age", 0))
                if rent_amt > 0:
                    start_m = months_until(age_now, r_start_age) if r_start_age > 0 else 0
                    end_m = months_until(age_now, r_end_age) if r_end_age > 0 else None
                    add_stream(start_m, end_m, rent_amt)

            # Windfalls: use the younger spouse's age as baseline for timing
            baseline_age = min(self_age, partner_age)
            windfalls = st.session_state.portfolio.get("windfalls", []) or []
            for wf in windfalls:
                amt = float(wf.get("amount", 0.0))
                age = int(wf.get("age", 0))
                if amt > 0 and age > 0:
                    m = max(0, int((age - baseline_age) * 12))
                    if m < T:
                        inc[m] += amt  # lump sum in that month

            return inc

        avg_withdrawals = None
        income_series = None
        if use_two_asset and use_taxed:
            # Taxed, ordered withdrawals; requires both equity and bond returns
            income_series = build_income_series(int(years_horizon * 12))
            balances, alive, avg_withdrawals = simulate_paths_two_asset_taxed(
                initial_taxable=init_taxable,
                initial_traditional=init_trad,
                initial_roth=init_roth,
                stock_returns=rets,
                bond_returns=bond_rets,
                years_horizon=int(years_horizon),
                years_until_retirement=int(years_until_ret),
                monthly_spend_now=monthly_spend_now,
                monthly_mortgage_now=mort,
                years_until_mortgage_end=int(years_until_mort_end),
                stock_weight=float(stock_weight),
                annual_rebalance=bool(annual_rebalance),
                ordinary_income_tax_rate=float(ordinary_tax),
                capital_gains_tax_rate=float(capg_tax),
                contribution_target=str(contrib_target),
                cfg=cfg,
                income_series=income_series,
            )
        elif use_two_asset:
            income_series = build_income_series(int(years_horizon * 12))
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
                income_series=income_series,
            )
        else:
            income_series = build_income_series(int(years_horizon * 12))
            balances, alive = simulate_paths(
                initial_balance=initial_balance,
                ret_series=rets,
                years_horizon=int(years_horizon),
                years_until_retirement=int(years_until_ret),
                monthly_spend_now=monthly_spend_now,
                monthly_mortgage_now=mort,
                years_until_mortgage_end=int(years_until_mort_end),
                cfg=cfg,
                income_series=income_series,
            )

        T = balances.shape[1]
        months = np.arange(T)
        # Percentiles
        p10 = np.percentile(balances, 10, axis=0)
        p50 = np.percentile(balances, 50, axis=0)
        p90 = np.percentile(balances, 90, axis=0)
        # Proportion of simulations that stayed alive through final month
        survival_path_alive = np.logical_and.accumulate(alive, axis=1)
        survival = survival_path_alive[:, -1].mean()

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

        # Visual guide: Withdrawal order and sources chart
        st.subheader("Withdrawal Order and Sources")
        st.markdown("- **Order**: Taxable → Traditional (taxed as ordinary income) → Roth (tax-free).\n- **Gross-up**: To deliver net spending after tax, taxable and traditional withdrawals are grossed up by their tax rates.")
        if avg_withdrawals is not None:
            # Aggregate monthly avg withdrawals to annual for display
            ann = []
            for y in years:
                start = y * 12
                end = min(T, (y + 1) * 12)
                sl = avg_withdrawals[start:end, :].sum(axis=0)
                ann.append({
                    "Year": y,
                    "Taxable": sl[0],
                    "Traditional": sl[1],
                    "Roth": sl[2],
                })
            ann_df = pd.DataFrame(ann)
            try:
                import altair as alt
                melted = ann_df.melt("Year", var_name="Bucket", value_name="Amount")
                chart = alt.Chart(melted).mark_area().encode(
                    x="Year:O",
                    y="Amount:Q",
                    color="Bucket:N"
                )
                st.altair_chart(chart, use_container_width=True)
            except Exception:
                st.area_chart(ann_df.set_index("Year"), height=240)
        else:
            st.info("Taxed withdrawal order visualization is available when both Equity and Bond returns are provided and taxes are enabled.")
