import os
from dataclasses import dataclass
from typing import Tuple
import numpy as np
import pandas as pd


@dataclass
class MCConfig:
    n_sims: int = 1000
    monthly_inflation: float = 0.002  # ~2.4% annual
    seed: int | None = 42
    monthly_contribution_now: float = 0.0  # household monthly contribution before retirement (today's dollars)
    annual_contribution_growth: float = 0.0  # e.g., 0.03 for 3%/yr


def load_monthly_returns(csv_path: str) -> pd.Series:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Historical returns CSV not found at {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["Date"])  # expects columns: Date, AdjClose, Return
    if "Return" not in df.columns:
        # compute if missing
        df["Return"] = df["AdjClose"].pct_change()
        df = df.dropna().reset_index(drop=True)
    if df["Return"].isna().all():
        raise ValueError("Historical returns series is empty or NaN")
    return df.set_index("Date")["Return"].dropna()


def _bootstrap_returns(ret_series: pd.Series, horizon_months: int, n_sims: int, rng: np.random.Generator) -> np.ndarray:
    # IID bootstrap: sample with replacement from historical monthly returns
    rets = ret_series.values
    idx = rng.integers(0, len(rets), size=(n_sims, horizon_months))
    sampled = rets[idx]
    return sampled  # shape (n_sims, T)


def _bootstrap_joint_indices(series_len: int, horizon_months: int, n_sims: int, rng: np.random.Generator) -> np.ndarray:
    """Return indices into historical series to sample the same months for multiple assets."""
    return rng.integers(0, series_len, size=(n_sims, horizon_months))


def build_spending_schedule(
    horizon_months: int,
    monthly_spend_now: float,
    monthly_mortgage: float,
    months_until_retirement: int,
    months_until_mortgage_end: int,
    monthly_inflation: float,
) -> np.ndarray:
    # Spending is zero before retirement; after retirement: basic+discretionary, plus mortgage until mortgage_end.
    spend = np.zeros(horizon_months, dtype=float)
    for t in range(horizon_months):
        # inflation-adjusted spending starting at retirement
        if t >= months_until_retirement:
            years = t / 12.0
            infl_factor = (1.0 + monthly_inflation) ** t
            base = monthly_spend_now * infl_factor
            mort = (monthly_mortgage * infl_factor) if t < months_until_mortgage_end else 0.0
            spend[t] = base + mort
    return spend


def build_contribution_schedule(
    horizon_months: int,
    monthly_contrib_now: float,
    months_until_retirement: int,
    annual_growth: float,
) -> np.ndarray:
    """Contributions occur only before retirement. Grow at the specified annual rate."""
    contrib = np.zeros(horizon_months, dtype=float)
    if monthly_contrib_now <= 0:
        return contrib
    monthly_growth = (1.0 + max(0.0, annual_growth)) ** (1.0 / 12.0) - 1.0
    amt = monthly_contrib_now
    for t in range(min(months_until_retirement, horizon_months)):
        contrib[t] = amt
        amt *= (1.0 + monthly_growth)
    return contrib


def simulate_paths(
    initial_balance: float,
    ret_series: pd.Series,
    years_horizon: int,
    years_until_retirement: int,
    monthly_spend_now: float,
    monthly_mortgage_now: float,
    years_until_mortgage_end: int,
    cfg: MCConfig,
    income_series: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
      balances: shape (n_sims, T) path of balances
      alive_mask: shape (n_sims, T) True if balance > 0
    """
    T = max(1, int(years_horizon * 12))
    months_until_ret = max(0, int(years_until_retirement * 12))
    months_until_mort_end = max(0, int(years_until_mortgage_end * 12))

    rng = np.random.default_rng(cfg.seed)
    boot = _bootstrap_returns(ret_series, T, cfg.n_sims, rng)  # (n_sims, T)

    spend = build_spending_schedule(
        horizon_months=T,
        monthly_spend_now=monthly_spend_now,
        monthly_mortgage=monthly_mortgage_now,
        months_until_retirement=months_until_ret,
        months_until_mortgage_end=months_until_mort_end,
        monthly_inflation=cfg.monthly_inflation,
    )  # (T,)
    if income_series is not None:
        spend = np.maximum(spend - income_series[:T], 0.0)
    contrib = build_contribution_schedule(
        horizon_months=T,
        monthly_contrib_now=cfg.monthly_contribution_now,
        months_until_retirement=months_until_ret,
        annual_growth=cfg.annual_contribution_growth,
    )  # (T,)

    balances = np.zeros((cfg.n_sims, T), dtype=float)
    # Month 0: add contribution first, then apply return, then withdraw spending
    balances[:, 0] = (max(0.0, initial_balance) + contrib[0]) * (1.0 + boot[:, 0]) - spend[0]

    for t in range(1, T):
        prev = np.maximum(balances[:, t - 1], 0.0) + contrib[t]
        growth = prev * (1.0 + boot[:, t])
        balances[:, t] = growth - spend[t]

    alive_mask = balances > 0.0
    path_avg_returns = boot.mean(axis=1)
    return balances, alive_mask, path_avg_returns


def simulate_paths_two_asset(
    initial_balance: float,
    stock_returns: pd.Series,
    bond_returns: pd.Series,
    years_horizon: int,
    years_until_retirement: int,
    monthly_spend_now: float,
    monthly_mortgage_now: float,
    years_until_mortgage_end: int,
    stock_weight: float,
    annual_rebalance: bool,
    cfg: MCConfig,
    income_series: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Two-asset simulation with optional annual rebalancing.

    Returns balances and alive mask with shape (n_sims, T).
    """
    T = max(1, int(years_horizon * 12))
    months_until_ret = max(0, int(years_until_retirement * 12))
    months_until_mort_end = max(0, int(years_until_mortgage_end * 12))

    rng = np.random.default_rng(cfg.seed)
    # Align series lengths
    s = stock_returns.dropna().values
    b = bond_returns.dropna().values
    m = min(len(s), len(b))
    if m < 24:
        raise ValueError("Not enough overlapping history for joint bootstrap (need >=24 months)")
    s = s[-m:]
    b = b[-m:]

    idx = _bootstrap_joint_indices(m, T, cfg.n_sims, rng)
    s_boot = s[idx]  # (n_sims, T)
    b_boot = b[idx]

    spend = build_spending_schedule(
        horizon_months=T,
        monthly_spend_now=monthly_spend_now,
        monthly_mortgage=monthly_mortgage_now,
        months_until_retirement=months_until_ret,
        months_until_mortgage_end=months_until_mort_end,
        monthly_inflation=cfg.monthly_inflation,
    )
    if income_series is not None:
        spend = np.maximum(spend - income_series[:T], 0.0)
    contrib = build_contribution_schedule(
        horizon_months=T,
        monthly_contrib_now=cfg.monthly_contribution_now,
        months_until_retirement=months_until_ret,
        annual_growth=cfg.annual_contribution_growth,
    )

    w_s = np.clip(float(stock_weight), 0.0, 1.0)
    w_b = 1.0 - w_s

    # Initialize per-asset balances
    balances_s = np.full((cfg.n_sims,), max(0.0, initial_balance) * w_s, dtype=float)
    balances_b = np.full((cfg.n_sims,), max(0.0, initial_balance) * w_b, dtype=float)

    balances_total = np.zeros((cfg.n_sims, T), dtype=float)
    # Month 0: add contribution split by target weights, then apply returns
    balances_s = (balances_s + contrib[0] * w_s) * (1.0 + s_boot[:, 0])
    balances_b = (balances_b + contrib[0] * w_b) * (1.0 + b_boot[:, 0])
    # Withdraw spending for month 0 proportionally to asset weights in portfolio
    total0 = np.maximum(balances_s + balances_b, 0.0)
    withdraw0 = spend[0]
    if withdraw0 > 0:
        share_s = np.divide(balances_s, total0, out=np.zeros_like(balances_s), where=total0>0)
        share_b = 1.0 - share_s
        balances_s -= withdraw0 * share_s
        balances_b -= withdraw0 * share_b
    balances_total[:, 0] = balances_s + balances_b

    for t in range(1, T):
        # Add contribution pre-retirement, split by target weights, then grow
        balances_s = (np.maximum(balances_s, 0.0) + contrib[t] * w_s) * (1.0 + s_boot[:, t])
        balances_b = (np.maximum(balances_b, 0.0) + contrib[t] * w_b) * (1.0 + b_boot[:, t])

        # Withdraw spending for month t
        total = np.maximum(balances_s + balances_b, 0.0)
        withdraw = spend[t]
        if withdraw > 0:
            share_s = np.divide(balances_s, total, out=np.zeros_like(balances_s), where=total>0)
            share_b = 1.0 - share_s
            balances_s -= withdraw * share_s
            balances_b -= withdraw * share_b

        # Rebalance annually (at year boundaries after growth/withdrawal)
        if annual_rebalance and (t % 12 == 0):
            total = np.maximum(balances_s + balances_b, 0.0)
            balances_s = total * w_s
            balances_b = total * w_b

        balances_total[:, t] = balances_s + balances_b

    alive_mask = balances_total > 0.0
    path_avg_returns = (w_s * s_boot + w_b * b_boot).mean(axis=1)
    return balances_total, alive_mask, path_avg_returns


def simulate_paths_two_asset_taxed(
    initial_taxable: float,
    initial_traditional: float,
    initial_roth: float,
    stock_returns: pd.Series,
    bond_returns: pd.Series,
    years_horizon: int,
    years_until_retirement: int,
    monthly_spend_now: float,
    monthly_mortgage_now: float,
    years_until_mortgage_end: int,
    stock_weight: float,
    annual_rebalance: bool,
    ordinary_income_tax_rate: float,  # applies to Traditional withdrawals
    capital_gains_tax_rate: float,    # applies to Taxable withdrawals (approx.)
    contribution_target: str,  # 'taxable' | 'traditional' | 'roth'
    cfg: MCConfig,
    income_series: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Simulate with three buckets and simple taxes.

    - Monthly portfolio return r = w_s*s + w_b*b applied to all buckets.
    - Withdrawals (net spending) follow order: Taxable -> Traditional -> Roth.
      For Taxable and Traditional, gross-up for taxes to meet net spending:
        gross = net / (1 - tax_rate). Roth is tax-free.

    Returns:
      balances_total: (n_sims, T)
      alive_mask: (n_sims, T)
      avg_withdrawals_by_bucket: (T, 3) average net withdrawal contribution from [Taxable, Traditional, Roth]
    """
    T = max(1, int(years_horizon * 12))
    months_until_ret = max(0, int(years_until_retirement * 12))
    months_until_mort_end = max(0, int(years_until_mortgage_end * 12))

    rng = np.random.default_rng(cfg.seed)
    s = stock_returns.dropna().values
    b = bond_returns.dropna().values
    m = min(len(s), len(b))
    if m < 24:
        raise ValueError("Not enough overlapping history for joint bootstrap (need >=24 months)")
    s = s[-m:]
    b = b[-m:]
    idx = _bootstrap_joint_indices(m, T, cfg.n_sims, rng)
    s_boot = s[idx]
    b_boot = b[idx]
    w_s = np.clip(float(stock_weight), 0.0, 1.0)
    w_b = 1.0 - w_s
    r_boot = w_s * s_boot + w_b * b_boot  # (n_sims, T)

    spend = build_spending_schedule(
        horizon_months=T,
        monthly_spend_now=monthly_spend_now,
        monthly_mortgage=monthly_mortgage_now,
        months_until_retirement=months_until_ret,
        months_until_mortgage_end=months_until_mort_end,
        monthly_inflation=cfg.monthly_inflation,
    )
    contrib = build_contribution_schedule(
        horizon_months=T,
        monthly_contrib_now=cfg.monthly_contribution_now,
        months_until_retirement=months_until_ret,
        annual_growth=cfg.annual_contribution_growth,
    )

    # Initialize buckets
    bal_tax = np.full((cfg.n_sims,), max(0.0, initial_taxable), dtype=float)
    bal_trad = np.full((cfg.n_sims,), max(0.0, initial_traditional), dtype=float)
    bal_roth = np.full((cfg.n_sims,), max(0.0, initial_roth), dtype=float)

    def add_contrib(b_tax, b_trad, b_roth, amount):
        if amount <= 0:
            return b_tax, b_trad, b_roth
        tgt = (contribution_target or 'traditional').lower()
        if tgt == 'taxable':
            b_tax += amount
        elif tgt == 'roth':
            b_roth += amount
        else:
            b_trad += amount
        return b_tax, b_trad, b_roth

    withdrawals_sum = np.zeros((T, 3), dtype=float)  # avg net withdrawals by bucket (Taxable, Traditional, Roth)
    balances_total = np.zeros((cfg.n_sims, T), dtype=float)

    # Month 0: contribution, grow, then withdraw
    bal_tax, bal_trad, bal_roth = add_contrib(bal_tax, bal_trad, bal_roth, contrib[0])
    bal_tax *= (1.0 + r_boot[:, 0])
    bal_trad *= (1.0 + r_boot[:, 0])
    bal_roth *= (1.0 + r_boot[:, 0])

    net_need = spend[0]
    w_tax = np.minimum(bal_tax, np.where(capital_gains_tax_rate < 1.0, net_need / (1 - capital_gains_tax_rate), 0.0))
    net_from_tax = np.minimum(net_need, w_tax * (1 - capital_gains_tax_rate))
    bal_tax -= w_tax
    net_need -= net_from_tax

    w_trad = np.minimum(bal_trad, np.where(ordinary_income_tax_rate < 1.0, net_need / (1 - ordinary_income_tax_rate), 0.0))
    net_from_trad = np.minimum(net_need, w_trad * (1 - ordinary_income_tax_rate))
    bal_trad -= w_trad
    net_need -= net_from_trad

    net_from_roth = np.minimum(net_need, bal_roth)
    bal_roth -= net_from_roth
    net_need -= net_from_roth

    withdrawals_sum[0, :] = np.array([net_from_tax, net_from_trad, net_from_roth]).mean()  # placeholder; corrected below per sim
    balances_total[:, 0] = bal_tax + bal_trad + bal_roth

    # For correct averages across sims, we compute per-sim then average at the end
    per_sim_withdrawals = np.zeros((cfg.n_sims, T, 3), dtype=float)
    per_sim_withdrawals[:, 0, 0] = net_from_tax  # broadcasting scalar per sim; approximation for month 0
    per_sim_withdrawals[:, 0, 1] = net_from_trad
    per_sim_withdrawals[:, 0, 2] = net_from_roth

    for t in range(1, T):
        # Contribution then growth
        if contrib[t] > 0:
            share = contrib[t]
            if contribution_target == 'taxable':
                bal_tax += share
            elif contribution_target == 'roth':
                bal_roth += share
            else:
                bal_trad += share

        bal_tax = np.maximum(bal_tax, 0.0) * (1.0 + r_boot[:, t])
        bal_trad = np.maximum(bal_trad, 0.0) * (1.0 + r_boot[:, t])
        bal_roth = np.maximum(bal_roth, 0.0) * (1.0 + r_boot[:, t])

        # Withdraw in order with tax gross-up
        net_need = np.full((cfg.n_sims,), spend[t], dtype=float)

        # From taxable
        w_tax_gross_cap = np.where(capital_gains_tax_rate < 1.0, net_need / (1 - capital_gains_tax_rate), 0.0)
        take_tax = np.minimum(bal_tax, w_tax_gross_cap)
        net_from_tax = np.minimum(net_need, take_tax * (1 - capital_gains_tax_rate))
        bal_tax -= take_tax
        net_need -= net_from_tax

        # From traditional
        w_trad_gross = np.where(ordinary_income_tax_rate < 1.0, net_need / (1 - ordinary_income_tax_rate), 0.0)
        take_trad = np.minimum(bal_trad, w_trad_gross)
        net_from_trad = np.minimum(net_need, take_trad * (1 - ordinary_income_tax_rate))
        bal_trad -= take_trad
        net_need -= net_from_trad

        # From Roth
        take_roth = np.minimum(bal_roth, net_need)
        net_from_roth = take_roth
        bal_roth -= take_roth
        net_need -= net_from_roth

        per_sim_withdrawals[:, t, 0] = net_from_tax
        per_sim_withdrawals[:, t, 1] = net_from_trad
        per_sim_withdrawals[:, t, 2] = net_from_roth

        # Rebalance annually (affects only asset mix; here returns already blended as r_boot)
        # No action needed since r_boot already reflects target weights; optional: real rebalance would ensure bucket growth uses target weights

        balances_total[:, t] = bal_tax + bal_trad + bal_roth

    # Alive mask and average withdrawals
    alive_mask = balances_total > 0.0
    avg_withdrawals = per_sim_withdrawals.mean(axis=0)  # (T, 3)
    path_avg_returns = r_boot.mean(axis=1)
    return balances_total, alive_mask, avg_withdrawals, path_avg_returns
