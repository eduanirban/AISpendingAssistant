from typing import List
import pandas as pd


def _fmt_currency(x: float) -> str:
    sign = '-' if x < 0 else ''
    x = abs(x)
    return f"{sign}${x:,.2f}"


def render_commentary(metrics: dict) -> List[str]:
    blocks: List[str] = []
    total_spend = metrics.get('total_spend', 0.0)
    total_income = metrics.get('total_income', 0.0)
    net = metrics.get('net', 0.0)

    blocks.append(f"- Total spend: {_fmt_currency(total_spend)} | Income: {_fmt_currency(total_income)} | Net: {_fmt_currency(net)}")

    by_cat = metrics.get('by_category')
    if isinstance(by_cat, pd.DataFrame) and not by_cat.empty:
        worst = by_cat.sort_values('amount').head(3)
        items = ", ".join([f"{r['category']}: {_fmt_currency(r['amount'])}" for _, r in worst.iterrows()])
        blocks.append(f"- Heaviest categories: {items}")

    anomalies = metrics.get('anomalies')
    if isinstance(anomalies, pd.DataFrame) and not anomalies.empty:
        blocks.append(f"- Spendy alerts: {len(anomalies)} transactions look unusually large. Review them.")

    by_month = metrics.get('by_month')
    if isinstance(by_month, pd.DataFrame) and len(by_month) >= 2:
        last2 = by_month.tail(2)['amount'].tolist()
        delta = last2[-1] - last2[-2]
        if abs(delta) > 0.01:
            direction = "up" if delta < 0 else "down"  # negative means more spend
            blocks.append(f"- Month-over-month net is {direction} by {_fmt_currency(abs(delta))}.")

    if not blocks:
        blocks.append("- Import data to see insights.")
    return blocks
