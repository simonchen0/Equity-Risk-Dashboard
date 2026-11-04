"""Entry point: `uv run streamlit run app/streamlit_app.py`."""

import streamlit as st
from components.state import init_state

from riskdash.analytics.returns import LOOKBACKS

st.set_page_config(page_title="Equity Risk Dashboard", page_icon="📈", layout="wide")
init_state()
st.html(
    """<style>
    [data-testid="stMetricValue"] { font-size: 1.65rem; font-variant-numeric: tabular-nums; }
    [data-testid="stMetricLabel"] p { font-size: 0.8rem; text-transform: uppercase;
        letter-spacing: .04em; color: #8b949e; }
    </style>"""
)

with st.sidebar:
    st.markdown("### Risk settings")
    st.segmented_control(
        "Lookback",
        options=list(LOOKBACKS),
        key="lookback_label",
        help="History used for beta, volatility and correlations (trading days: "
        + ", ".join(f"{k}={v}" for k, v in LOOKBACKS.items())
        + ").",
    )
    st.toggle(
        "Blume-adjusted beta",
        key="blume",
        help="Shrinks raw beta toward 1: 0.67 × raw + 0.33 (Bloomberg's 'adjusted beta').",
    )
    st.caption("Prices: Yahoo Finance via yfinance, delayed. Not for live trading decisions.")

nav = st.navigation(
    [
        st.Page("views/overview.py", title="Overview", icon=":material/dashboard:", default=True),
        st.Page("views/risk.py", title="Risk", icon=":material/analytics:"),
        st.Page("views/scenarios.py", title="Scenarios", icon=":material/trending_down:"),
        st.Page("views/hedging.py", title="Hedging", icon=":material/shield:"),
        st.Page("views/alerts.py", title="Alerts", icon=":material/notifications:"),
        st.Page("views/positions.py", title="Positions", icon=":material/edit_note:"),
    ]
)
nav.run()
