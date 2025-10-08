import streamlit as st


def currency_input(label: str, key: str, value: float = 0.0, help_text: str | None = None) -> float:
    """Standardized currency input with consistent formatting and step."""
    return st.number_input(label, min_value=0.0, value=float(value), step=1000.0, format="%.2f", key=key, help=help_text)
