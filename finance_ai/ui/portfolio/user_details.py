import streamlit as st
from .state import init_portfolio_state


def render_user_details():
    init_portfolio_state()

    st.subheader("Household Details")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**You**")
        st.session_state.portfolio["user"]["self"]["age"] = st.number_input(
            "Your current age", min_value=18, max_value=100,
            value=st.session_state.portfolio["user"]["self"]["age"], step=1,
            help="Enter your current age.", key="ud_self_age"
        )
        st.session_state.portfolio["user"]["self"]["retirement_age"] = st.number_input(
            "Your target retirement age", min_value=30, max_value=90,
            value=st.session_state.portfolio["user"]["self"]["retirement_age"], step=1,
            help="Age at which you plan to retire.", key="ud_self_ret_age"
        )
        st.session_state.portfolio["user"]["self"]["life_expectancy"] = st.number_input(
            "Your life expectancy", min_value=60, max_value=110,
            value=st.session_state.portfolio["user"]["self"]["life_expectancy"], step=1,
            help="Expected age you might live to.", key="ud_self_le"
        )
    with c2:
        st.markdown("**Partner**")
        st.session_state.portfolio["user"]["partner"]["age"] = st.number_input(
            "Partner current age", min_value=18, max_value=100,
            value=st.session_state.portfolio["user"]["partner"]["age"], step=1,
            help="Enter partner's current age.", key="ud_partner_age"
        )
        st.session_state.portfolio["user"]["partner"]["retirement_age"] = st.number_input(
            "Partner target retirement age", min_value=30, max_value=90,
            value=st.session_state.portfolio["user"]["partner"]["retirement_age"], step=1,
            help="Age at which your partner plans to retire.", key="ud_partner_ret_age"
        )
        st.session_state.portfolio["user"]["partner"]["life_expectancy"] = st.number_input(
            "Partner life expectancy", min_value=60, max_value=110,
            value=st.session_state.portfolio["user"]["partner"]["life_expectancy"], step=1,
            help="Expected age partner might live to.", key="ud_partner_le"
        )

    self_le = st.session_state.portfolio["user"]["self"]["life_expectancy"]
    partner_le = st.session_state.portfolio["user"]["partner"]["life_expectancy"]
    joint_le = max(self_le, partner_le)
    st.session_state.portfolio["user"]["joint_life_expectancy"] = joint_le

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Your retirement in", f"{max(0, st.session_state.portfolio['user']['self']['retirement_age'] - st.session_state.portfolio['user']['self']['age'])} yrs")
    with m2:
        st.metric("Partner retirement in", f"{max(0, st.session_state.portfolio['user']['partner']['retirement_age'] - st.session_state.portfolio['user']['partner']['age'])} yrs")
    with m3:
        st.metric("Joint life expectancy", f"{joint_le} years")

    st.info("Joint life expectancy is the maximum of both spouse life expectancies.")
