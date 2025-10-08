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


def simulate_paths(
    initial_balance: float,
    ret_series: pd.Series,
    years_horizon: int,
    years_until_retirement: int,
    monthly_spend_now: float,
    monthly_mortgage_now: float,
    years_until_mortgage_end: int,
    cfg: MCConfig,
) -> Tuple[np.ndarray, np.ndarray]:
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

    balances = np.zeros((cfg.n_sims, T), dtype=float)
    balances[:, 0] = max(0.0, initial_balance) * (1.0 + boot[:, 0]) - spend[0]

    for t in range(1, T):
        prev = np.maximum(balances[:, t - 1], 0.0)
        growth = prev * (1.0 + boot[:, t])
        balances[:, t] = growth - spend[t]

    alive_mask = balances > 0.0
    return balances, alive_mask


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

    w_s = np.clip(float(stock_weight), 0.0, 1.0)
    w_b = 1.0 - w_s

    # Initialize per-asset balances
    balances_s = np.full((cfg.n_sims,), max(0.0, initial_balance) * w_s, dtype=float)
    balances_b = np.full((cfg.n_sims,), max(0.0, initial_balance) * w_b, dtype=float)

    balances_total = np.zeros((cfg.n_sims, T), dtype=float)
    # Month 0
    balances_s = balances_s * (1.0 + s_boot[:, 0])
    balances_b = balances_b * (1.0 + b_boot[:, 0])
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
        # Growth
        balances_s = np.maximum(balances_s, 0.0) * (1.0 + s_boot[:, t])
        balances_b = np.maximum(balances_b, 0.0) * (1.0 + b_boot[:, t])

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
    return balances_total, alive_mask
