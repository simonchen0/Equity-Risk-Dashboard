"""Entry point: `uv run streamlit run app/streamlit_app.py`."""

from pathlib import Path

import streamlit as st
from components.state import init_state
from components.theme import inject_css

from riskdash.analytics.returns import LOOKBACKS

st.set_page_config(
    page_title="Equity Risk Dashboard",
    page_icon=str(Path(__file__).parent / "assets" / "favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_state()
inject_css()

nav = st.navigation(
    [
        st.Page("views/overview.py", title="Overview", icon=":material/dashboard:", default=True),
        st.Page("views/risk.py", title="Risk", icon=":material/analytics:"),
        st.Page("views/scenarios.py", title="Scenarios", icon=":material/trending_down:"),
        st.Page("views/hedging.py", title="Hedging", icon=":material/shield:"),
        st.Page("views/alerts.py", title="Alerts", icon=":material/notifications:"),
        st.Page("views/positions.py", title="Positions", icon=":material/edit_note:"),
    ],
    position="top",
)

# Risk settings apply to every page, so they sit in one slim strip under the top bar.
label_col, lookback_col, blume_col, _ = st.columns([2, 4, 5, 8], vertical_alignment="center")
label_col.markdown('<span class="control-label">Lookback</span>', unsafe_allow_html=True)
lookback_col.segmented_control(
    "Lookback",
    options=list(LOOKBACKS),
    key="lookback_label",
    label_visibility="collapsed",
    help="History used for beta, volatility and correlations (trading days: "
    + ", ".join(f"{k}={v}" for k, v in LOOKBACKS.items())
    + ").",
)
blume_col.toggle(
    "Blume-adjusted beta",
    key="blume",
    help="Shrinks raw beta toward 1: 0.67 × raw + 0.33 (Bloomberg's 'adjusted beta').",
)

nav.run()
st.html(
    '<div class="footer-note">Prices: Yahoo Finance via yfinance, delayed. '
    "Not for live trading decisions.</div>"
)
