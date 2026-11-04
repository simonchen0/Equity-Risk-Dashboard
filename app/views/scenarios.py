import plotly.graph_objects as go
import streamlit as st
from components import format as fmt
from components.charts import CONFIG, style
from components.state import names, require_snapshot
from components.theme import kpi_strip, table_height

from riskdash.analytics.scenarios import DEFAULT_SHOCKS, position_pnl, scenario_grid

st.title("Scenarios")
snap = require_snapshot()
v = snap.valuation
pos = snap.positions
mv, betas = pos["market_value"], snap.betas

st.caption(
    "Estimated P&L if the S&P 500 moves instantly, using each position's beta: "
    "market value × beta × move. A linear, market-only estimate: it ignores stock-specific "
    "moves, volatility changes, and betas shifting in large sell-offs."
)

# --- Shock grid -------------------------------------------------------------------------
st.subheader("S&P 500 shock grid")
grid = scenario_grid(mv, betas, v.nav, DEFAULT_SHOCKS)
labels = [fmt.pct(s, 1, signed=True) if s else "0%" for s in grid.index]

fig = go.Figure(
    go.Bar(
        x=labels,
        y=grid["pnl"],
        marker_color=[fmt.POS if x >= 0 else fmt.NEG for x in grid["pnl"]],
        customdata=grid["pnl_pct_nav"],
        hovertemplate="S&P %{x}<br>P&L %{y:$,.0f} (%{customdata:+.2%} of NAV)<extra></extra>",
    )
)
style(fig, height=320, pct_axis=None)
fig.update_layout(bargap=0.35)
fig.update_xaxes(title="S&P 500 move", type="category", showgrid=False)
fig.update_yaxes(tickformat="$,.2~s", title="Portfolio P&L")
st.plotly_chart(fig, width="stretch", config=CONFIG)

table = grid.rename(columns={"pnl": "P&L", "pnl_pct_nav": "% of NAV"})
table.index = labels
st.dataframe(
    table.T.style.format(
        {c: (lambda x: fmt.money(x, signed=True)) for c in table.index},
        subset=(["P&L"], slice(None)),
    ).format(
        {c: (lambda x: fmt.pct(x, 2, signed=True)) for c in table.index},
        subset=(["% of NAV"], slice(None)),
    ),
    width="stretch",
    row_height=28,
    height=table_height(2),
)

# --- Custom shock -----------------------------------------------------------------------
st.subheader("Custom scenario")
shock_pct = st.columns([1, 4])[0].number_input(
    "S&P 500 move (%)", min_value=-60.0, max_value=60.0, value=-10.0, step=1.0, format="%.1f"
)
shock = shock_pct / 100
by_pos = position_pnl(mv, betas, [shock])[shock]
total = by_pos.sum()

kpi_strip(
    [
        dict(label="Portfolio P&L", value=fmt.md(fmt.compact_money(total, signed=True))),
        dict(label="% of NAV", value=fmt.pct(total / v.nav, 2, signed=True)),
        dict(
            label="Beta-implied portfolio move",
            value=fmt.pct(snap.portfolio_beta * shock, 2, signed=True),
            delta=f"β {fmt.num(snap.portfolio_beta)} × {fmt.pct(shock, 1, signed=True)}",
            delta_color="off",
            delta_arrow="off",
            help="Same number as % of NAV: portfolio beta × S&P move.",
        ),
    ],
    key="scenario",
)

detail = pos[["market_value", "weight", "beta"]].copy()
detail.insert(0, "name", detail.index.map(names(list(detail.index))))
detail["pnl"] = by_pos
detail["pnl_pct_nav"] = by_pos / v.nav
detail = detail.sort_values("pnl")  # biggest losses first
st.dataframe(
    detail.style.format(
        {
            "market_value": fmt.money,
            "weight": lambda x: fmt.pct(x, 1),
            "beta": fmt.num,
            "pnl": lambda x: fmt.money(x, signed=True),
            "pnl_pct_nav": lambda x: fmt.pct(x, 2, signed=True),
        },
        na_rep="—",
    ).map(fmt.pnl_color, subset=["pnl", "pnl_pct_nav"]),
    width="stretch",
    height=table_height(len(detail), max_rows=16),
    row_height=28,
    column_config={
        "_index": st.column_config.Column("Ticker", pinned=True),
        "name": "Name",
        "market_value": "Mkt value",
        "weight": "Weight",
        "beta": "Beta",
        "pnl": "Scenario P&L",
        "pnl_pct_nav": "% of NAV",
    },
)
st.caption("Shorts with positive beta gain when the market falls, offsetting long losses.")
