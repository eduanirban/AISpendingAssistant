import streamlit as st
import pandas as pd
from .state import init_portfolio_state


def render_income():
    init_portfolio_state()

    st.subheader("Household Income")
    st.caption("Annual pre-tax income sources for each spouse.")
    for who in ["self", "partner"]:
        st.markdown(f"**{'You' if who=='self' else 'Partner'} Income**")
        c1, c2, c3 = st.columns(3)
        st.session_state.portfolio["income"][who]["salary"] = c1.number_input(
            "Salary", min_value=0.0, value=float(st.session_state.portfolio["income"][who]["salary"]), step=1000.0, format="%.2f",
            help="Annual W-2 or self-employment income", key=f"inc_{who}_salary"
        )
        st.session_state.portfolio["income"][who]["rental"] = c2.number_input(
            "Rental income", min_value=0.0, value=float(st.session_state.portfolio["income"][who]["rental"]), step=500.0, format="%.2f",
            help="Net annual rental income", key=f"inc_{who}_rental"
        )
        st.session_state.portfolio["income"][who]["pension"] = c3.number_input(
            "Pension", min_value=0.0, value=float(st.session_state.portfolio["income"][who]["pension"]), step=500.0, format="%.2f",
            help="Annual pension income (once in pay)", key=f"inc_{who}_pension"
        )

        # Start ages (compact row)
        a1, a2 = st.columns(2)
        st.session_state.portfolio["income"][who]["rental_start_age"] = a1.number_input(
            "Rental start age (0 = now)", min_value=0, max_value=110,
            value=int(st.session_state.portfolio["income"][who].get("rental_start_age", 0)), step=1,
            key=f"inc_{who}_rental_start_age"
        )
        st.session_state.portfolio["income"][who]["pension_start_age"] = a2.number_input(
            "Pension start age", min_value=0, max_value=110,
            value=int(st.session_state.portfolio["income"][who].get("pension_start_age", 0)), step=1,
            key=f"inc_{who}_pension_start_age"
        )

    # Summary
    total_self = sum(st.session_state.portfolio["income"]["self"].values())
    total_partner = sum(st.session_state.portfolio["income"]["partner"].values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Your annual income", f"${total_self:,.0f}")
    m2.metric("Partner annual income", f"${total_partner:,.0f}")
    m3.metric("Household income", f"${(total_self + total_partner):,.0f}")

    st.markdown("---")
    st.subheader("Windfalls (one-time)")
    st.caption("Enter one-time lump sums such as property sale or downsizing proceeds.")

    windfalls = st.session_state.portfolio.get("windfalls", []) or []
    df = pd.DataFrame(windfalls, columns=["label", "amount", "age"]).rename(columns={
        "label": "Label", "amount": "Amount", "age": "Age"
    })

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Label": st.column_config.TextColumn(required=False),
            "Amount": st.column_config.NumberColumn(min_value=0.0, step=1000.0, format="%.2f"),
            "Age": st.column_config.NumberColumn(min_value=0, max_value=120, step=1),
        },
        hide_index=True,
    )

    # Persist back
    clean = []
    for _, row in edited.fillna({"Label": "", "Amount": 0.0, "Age": 0}).iterrows():
        label = str(row["Label"]).strip()
        amount = float(row["Amount"]) if pd.notna(row["Amount"]) else 0.0
        age = int(row["Age"]) if pd.notna(row["Age"]) else 0
        if label or amount > 0:
            clean.append({"label": label, "amount": amount, "age": age})
    st.session_state.portfolio["windfalls"] = clean
