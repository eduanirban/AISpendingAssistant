import streamlit as st
import pandas as pd
import altair as alt


def render_overview_cards(metrics: dict):
    total_spend = metrics.get('total_spend', 0.0)
    total_income = metrics.get('total_income', 0.0)
    net = metrics.get('net', 0.0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spend", f"${abs(total_spend):,.2f}")
    c2.metric("Total Income", f"${abs(total_income):,.2f}")
    c3.metric("Net", f"${net:,.2f}")


def render_charts(df: pd.DataFrame, metrics: dict):
    by_month = metrics.get('by_month')
    if isinstance(by_month, pd.DataFrame) and not by_month.empty:
        st.subheader("Net by Month")
        chart = alt.Chart(by_month).mark_bar().encode(
            x='month:T',
            y='amount:Q',
            tooltip=['month', 'amount']
        )
        st.altair_chart(chart, use_container_width=True)

    by_category = metrics.get('by_category')
    if isinstance(by_category, pd.DataFrame) and not by_category.empty:
        st.subheader("Spend by Category")
        # Only debits
        bc = by_category.copy()
        bc = bc[bc['amount'] < 0]
        chart = alt.Chart(bc).mark_bar().encode(
            x=alt.X('amount:Q', title='Amount'),
            y=alt.Y('category:N', sort='-x'),
            tooltip=['category', 'amount']
        )
        st.altair_chart(chart, use_container_width=True)

    anomalies = metrics.get('anomalies')
    if isinstance(anomalies, pd.DataFrame) and not anomalies.empty:
        st.subheader("Anomalies")
        st.dataframe(anomalies[['date','description','amount','category','merchant']].sort_values('amount'))


def render_transactions_table(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("No transactions in the selected period.")
        return
    st.dataframe(
        df.sort_values('date', ascending=False),
        use_container_width=True,
        height=420
    )
