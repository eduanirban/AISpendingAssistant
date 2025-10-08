import streamlit as st
from .state import init_portfolio_state


def _windfall_key(i: int, field: str) -> str:
    return f"wf_{i}_{field}"


def render_other_income():
    init_portfolio_state()

    st.subheader("Other Income: Rental & Windfalls")
    st.caption("Configure recurring rental income windows and any one-time windfalls.")

    # Rental per spouse with start/end ages
    for who in ["self", "partner"]:
        with st.expander(f"{'You' if who=='self' else 'Partner'} Rental", expanded=(who == "self")):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.session_state.portfolio["income"][who]["rental"] = st.number_input(
                    "Rental (annual)", min_value=0.0,
                    value=float(st.session_state.portfolio["income"][who]["rental"]), step=500.0, format="%.2f",
                    key=f"oi_{who}_rent_amt",
                )
            with c2:
                st.session_state.portfolio["income"][who]["rental_start_age"] = st.number_input(
                    "Start age (0 = now)", min_value=0, max_value=110,
                    value=int(st.session_state.portfolio["income"][who]["rental_start_age"]), step=1,
                    key=f"oi_{who}_rent_start",
                )
            with c3:
                st.session_state.portfolio["income"][who]["rental_end_age"] = st.number_input(
                    "End age (0 = none)", min_value=0, max_value=120,
                    value=int(st.session_state.portfolio["income"][who]["rental_end_age"]), step=1,
                    key=f"oi_{who}_rent_end",
                )

    st.markdown("---")
    st.subheader("Windfalls (one-time)")
    st.caption("Add one-time lump sums such as property sale or downsizing proceeds.")

    # Add new windfall
    with st.form("add_windfall", clear_on_submit=True):
        wc1, wc2, wc3 = st.columns([2,1,1])
        label = wc1.text_input("Label", key="wf_new_label")
        amount = wc2.number_input("Amount", min_value=0.0, step=1000.0, format="%.2f", key="wf_new_amount")
        age = wc3.number_input("Age at receipt", min_value=0, max_value=120, step=1, key="wf_new_age")
        add_btn = st.form_submit_button("Add windfall")
        if add_btn and label and amount > 0:
            st.session_state.portfolio.setdefault("windfalls", []).append({
                "label": label,
                "amount": float(amount),
                "age": int(age),
            })

    # List and edit existing windfalls
    windfalls = st.session_state.portfolio.get("windfalls", [])
    if not windfalls:
        st.info("No windfalls added yet.")
        return

    for i, wf in enumerate(list(windfalls)):
        with st.expander(f"{wf.get('label','(unnamed)')} — ${wf.get('amount',0):,.0f} at age {wf.get('age',0)}", expanded=False):
            ec1, ec2, ec3, ec4 = st.columns([2,1,1,1])
            wf["label"] = ec1.text_input("Label", value=wf.get("label", ""), key=_windfall_key(i, "label"))
            wf["amount"] = ec2.number_input("Amount", min_value=0.0, value=float(wf.get("amount", 0.0)), step=1000.0, format="%.2f", key=_windfall_key(i, "amount"))
            wf["age"] = ec3.number_input("Age", min_value=0, max_value=120, value=int(wf.get("age", 0)), step=1, key=_windfall_key(i, "age"))
            if ec4.button("Remove", key=_windfall_key(i, "remove")):
                st.session_state.portfolio["windfalls"].pop(i)
                st.experimental_rerun()
