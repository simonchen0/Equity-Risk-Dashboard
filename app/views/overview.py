import plotly.graph_objects as go
import streamlit as st
from components import format as fmt
from components.charts import CONFIG, style
from components.state import current_alerts, names, require_snapshot, sector_map
from components.theme import kpi_strip, status_line, table_height

st.title("Portfolio overview")
snap = require_snapshot()
v = snap.valuation

status_col, link_col = st.columns([5, 1], vertical_alignment="top")
with status_col:
    status_line(current_alerts(snap))
link_col.page_link("views/alerts.py", label="Edit limits", icon=":material/tune:")

# --- KPI header -------------------------------------------------------------------------
kpi_strip(
    [
        dict(label="NAV", value=fmt.md(fmt.compact_money(v.nav))),
        dict(
            label="Day P&L",
            value=fmt.md(fmt.compact_money(v.day_pnl, signed=True)),
            delta=fmt.pct(v.day_return, signed=True),
            help="Mark-to-market vs previous close, assuming no trades today.",
        ),
        dict(
            label="Unrealized P&L",
            value=fmt.md(fmt.compact_money(v.unrealized_pnl, signed=True)),
            help="vs average cost, for positions that have one.",
        ),
        dict(
            label="Beta (vs SPY)",
            value=fmt.num(snap.portfolio_beta),
            delta=fmt.md(f"β-$ {fmt.compact_money(snap.dollar_beta)}"),
            delta_color="off",
            delta_arrow="off",
            help="Σ weight × beta. β-$ (dollar beta) = Σ market value × beta: the beta-equivalent "
            "dollar exposure to the S&P 500.",
        ),
        dict(
            label="Volatility (ann.)",
            value=fmt.pct(snap.portfolio_vol, 1),
            delta=fmt.md(f"1-day 1σ ≈ {fmt.compact_money(snap.portfolio_vol / 252**0.5 * v.nav)}"),
            delta_color="off",
            delta_arrow="off",
            help="√(wᵀΣw) on daily returns × √252, using current weights.",
        ),
        dict(
            label="Gross / Net",
            value=f"{fmt.pct(v.gross_exposure, 0)} / {fmt.pct(v.net_exposure, 0)}",
            delta=fmt.md(f"L {fmt.compact_money(v.long_mv)} · S {fmt.compact_money(v.short_mv)}"),
            delta_color="off",
            delta_arrow="off",
        ),
    ],
    key="overview",
)

# --- Charts -----------------------------------------------------------------------------
pos = snap.positions


def bar(series, title, help_text):
    s = series.sort_values()
    fig = go.Figure(
        go.Bar(
            x=s.values,
            y=s.index,
            orientation="h",
            marker_color=[fmt.POS if x >= 0 else fmt.NEG for x in s.values],
            hovertemplate="%{y}: %{x:.2%}<extra></extra>",
        )
    )
    style(fig, height=17 * len(s) + 40).update_yaxes(tickfont=dict(family="monospace"))
    st.subheader(title, help=help_text)
    st.plotly_chart(fig, width="stretch", config=CONFIG)


left, right = st.columns(2)
with left:
    bar(pos["weight"], "Weights", "Market value as % of NAV (shorts negative).")
with right:
    bar(
        pos["beta_adj_exposure"],
        "Beta-adjusted exposure",
        "Weight × beta: each position's contribution to portfolio beta "
        f"({fmt.num(snap.portfolio_beta)} in total).",
    )


# --- Holdings ---------------------------------------------------------------------------
tickers = list(pos.index)
pos.insert(0, "name", pos.index.map(names(tickers)))
pos.insert(1, "sector", pos.index.map(sector_map(tickers)))
pos = pos.sort_values("market_value", key=abs, ascending=False)

st.subheader("Holdings")
table = pos[
    [
        "name",
        "sector",
        "quantity",
        "price",
        "day_change_pct",
        "market_value",
        "weight",
        "day_pnl",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "beta",
        "vol",
        "risk_contrib",
    ]
]
PNL_COLS = ["day_change_pct", "day_pnl", "unrealized_pnl", "unrealized_pnl_pct"]
styled = table.style.format(
    {
        "quantity": "{:,.0f}",
        "price": "${:,.2f}",
        "day_change_pct": lambda x: fmt.pct(x, signed=True),
        "market_value": fmt.money,
        "weight": lambda x: fmt.pct(x, 1),
        "day_pnl": lambda x: fmt.money(x, signed=True),
        "unrealized_pnl": lambda x: fmt.money(x, signed=True),
        "unrealized_pnl_pct": lambda x: fmt.pct(x, 1, signed=True),
        "beta": "{:.2f}",
        "vol": lambda x: fmt.pct(x, 1),
        "risk_contrib": lambda x: fmt.pct(x, 1),
    },
    na_rep="—",
).map(fmt.pnl_color, subset=PNL_COLS)
st.dataframe(
    styled,
    width="stretch",
    height=table_height(len(table), max_rows=16),
    row_height=28,
    column_config={
        "_index": st.column_config.Column("Ticker", pinned=True),
        "name": "Name",
        "sector": "Sector",
        "quantity": "Qty",
        "price": "Last",
        "day_change_pct": "Day %",
        "market_value": "Mkt value",
        "weight": st.column_config.Column("Weight", help="Market value / NAV"),
        "day_pnl": "Day P&L",
        "unrealized_pnl": "Unrl P&L",
        "unrealized_pnl_pct": "Unrl %",
        "beta": "Beta",
        "vol": st.column_config.Column("Vol", help="Annualized volatility"),
        "risk_contrib": st.column_config.Column(
            "Risk %", help="Share of portfolio variance: wᵢ(Σw)ᵢ / wᵀΣw. Negative = diversifier."
        ),
    },
)
st.caption(f"Cash {fmt.money(v.cash)} · {len(table)} positions")
