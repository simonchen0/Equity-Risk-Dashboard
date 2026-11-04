import streamlit as st
from components.state import get_portfolio, load_demo, set_portfolio

from riskdash.portfolio.io import (
    PortfolioImportError,
    portfolio_from_frame,
    portfolio_to_csv,
    portfolio_to_frame,
    read_portfolio_csv,
)

st.title("Positions")
st.caption(
    "Quantity > 0 is long, < 0 is short. Average cost is optional (needed for unrealized P&L). "
    "Sector overrides the vendor classification."
)

pf = get_portfolio()
version = st.session_state.portfolio_version
frame = portfolio_to_frame(pf)
frame = frame[frame["ticker"] != "CASH"].reset_index(drop=True)

with st.form(f"positions_form_{version}"):
    edited = st.data_editor(
        frame,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", required=True, max_chars=10),
            "quantity": st.column_config.NumberColumn("Quantity", required=True, format="%,.0f"),
            "avg_cost": st.column_config.NumberColumn("Avg cost", min_value=0.0, format="$%.2f"),
            "sector": st.column_config.TextColumn("Sector override"),
        },
        key=f"editor_{version}",
    )
    cash = st.number_input("Cash balance ($)", value=float(pf.cash), step=10_000.0, format="%.2f")
    if st.form_submit_button("Apply changes", type="primary"):
        rows = edited.copy()
        rows.loc[len(rows)] = {"ticker": "CASH", "quantity": cash}
        try:
            set_portfolio(portfolio_from_frame(rows))
        except PortfolioImportError as exc:
            for e in exc.errors:
                st.error(e)
        else:
            st.toast("Portfolio updated")
            st.rerun()

st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Import CSV**")
    upload = st.file_uploader(
        "Columns: ticker, quantity, avg_cost, sector. Cash as a `CASH` row.",
        type="csv",
        key=f"upload_{version}",
    )
    if upload is not None:
        try:
            set_portfolio(read_portfolio_csv(upload))
        except PortfolioImportError as exc:
            for e in exc.errors:
                st.error(e)
        else:
            st.toast(f"Imported {upload.name}")
            st.rerun()
with c2:
    st.markdown("**Export CSV**")
    st.download_button(
        "Download portfolio.csv",
        portfolio_to_csv(pf),
        file_name="portfolio.csv",
        mime="text/csv",
        icon=":material/download:",
    )
with c3:
    st.markdown("**Demo book**")
    if st.button("Reset to demo portfolio", icon=":material/restart_alt:"):
        load_demo()
        st.rerun()
