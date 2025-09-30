import pandas as pd


def compute_insights(df: pd.DataFrame) -> dict:
    metrics = {
        'total_spend': 0.0,
        'total_income': 0.0,
        'net': 0.0,
        'by_month': pd.DataFrame(),
        'by_category': pd.DataFrame(),
        'top_merchants': pd.DataFrame(),
        'anomalies': pd.DataFrame(),
    }
    if df is None or df.empty:
        return metrics

    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M').dt.to_timestamp()

    spend = df.loc[df['amount'] < 0, 'amount'].sum()
    income = df.loc[df['amount'] > 0, 'amount'].sum()
    metrics['total_spend'] = float(spend)
    metrics['total_income'] = float(income)
    metrics['net'] = float(income + spend)

    metrics['by_month'] = df.groupby('month')['amount'].sum().reset_index()

    if 'category' in df.columns:
        metrics['by_category'] = df.groupby('category')['amount'].sum().reset_index().sort_values('amount')
    if 'merchant' in df.columns:
        merchants = df.groupby('merchant')['amount'].sum().reset_index()
        metrics['top_merchants'] = merchants.sort_values('amount').head(10)

    # Simple anomaly detection: flag debits more extreme than mean-2*std (more negative)
    debits = df[df['amount'] < 0].copy()
    if not debits.empty:
        mu = debits['amount'].mean()
        sigma = debits['amount'].std(ddof=0) or 1.0
        threshold = mu - 2 * sigma
        anomalies = debits[debits['amount'] < threshold]
        metrics['anomalies'] = anomalies.sort_values('amount').head(20)

    return metrics
