import pandas as pd
import streamlit as st
from components import format as fmt
from components.state import hedge_prices, require_snapshot
from components.theme import kpi_strip

from riskdash.analytics.hedging import (
    ES_MULTIPLIER,
    MES_MULTIPLIER,
    hedged_vol,
    hedged_weights,
    size_hedge,
)
from riskdash.analytics.scenarios import DEFAULT_SHOCKS
from riskdash.analytics.volatility import annualized_cov

st.title("Hedging")
snap = require_snapshot()
v = snap.valuation
pb, nav = snap.portfolio_beta, v.nav

st.caption(
    "How much SPY or S&P 500 futures to trade to move the portfolio to a target beta: "
    "(target β − current β) × NAV. Assumes the hedge moves one-for-one with the S&P 500; "
    "ignores basis, futures carry, dividends, financing and margin."
)

prices = hedge_prices()
if "SPY" not in prices:
    st.error(
        "Couldn't load the SPY price, so the hedge can't be sized right now. Try again shortly."
    )
    st.stop()

kpi_strip(
    [
        dict(label="Current beta", value=fmt.num(pb)),
        dict(
            label="Dollar beta",
            value=fmt.md(fmt.compact_money(snap.dollar_beta)),
            help="Dollar exposure to the S&P 500 implied by beta: P&L per 100% S&P move.",
        ),
        dict(label="NAV", value=fmt.md(fmt.compact_money(nav))),
    ],
    key="hedging",
)

# --- Inputs -----------------------------------------------------------------------------
left, right = st.columns([1, 2])
with left:
    target = st.number_input(
        "Target beta",
        min_value=-1.0,
        max_value=3.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        help="0.00 = market-neutral. Above the current beta means buying exposure.",
    )

instruments = {"SPY": ("SPY shares", prices["SPY"])}
if "ES=F" in prices:
    instruments["ES"] = ("E-mini S&P 500 (ES) contracts", prices["ES=F"] * ES_MULTIPLIER)
    instruments["MES"] = ("Micro E-mini (MES) contracts", prices["ES=F"] * MES_MULTIPLIER)
else:
    st.info("Futures prices are unavailable right now; only SPY is shown.")

with right:
    choice = st.segmented_control(
        "Hedge instrument", list(instruments), default="SPY", selection_mode="single"
    )
choice = choice or "SPY"

sizings = {k: size_hedge(target, pb, nav, unit) for k, (_, unit) in instruments.items()}

# --- Sizing table -----------------------------------------------------------------------
st.subheader("Hedge sizing")
rows = []
for k, (label, unit) in instruments.items():
    s = sizings[k]
    rows.append(
        {
            "Instrument": label,
            "Per unit": unit,
            "Exact": s.exact_units,
            "Trade": s.units,
            "Notional": s.notional,
            "Beta after": s.post_beta,
            "Rounding gap": s.residual_beta,
        }
    )
table = pd.DataFrame(rows).set_index("Instrument")
st.dataframe(
    table.style.format(
        {
            "Per unit": lambda x: fmt.money(x, 2),
            "Exact": lambda x: f"{x:+,.1f}",
            "Trade": lambda x: f"{x:+,d}",
            "Notional": lambda x: fmt.money(x, signed=True),
            "Beta after": fmt.num,
            "Rounding gap": lambda x: f"{x:+.3f}",
        }
    ),
    width="stretch",
    row_height=28,
    column_config={
        "Per unit": st.column_config.Column(
            "Exposure per unit",
            help="SPY: share price. Futures: index level × multiplier ($50 ES, $5 MES).",
        ),
        "Exact": st.column_config.Column("Exact units", help="Negative = sell"),
        "Trade": st.column_config.Column("Whole units", help="Rounded to the nearest whole unit"),
        "Rounding gap": st.column_config.Column(
            "Beta vs target", help="Beta left over from trading whole units only."
        ),
    },
)

sel = sizings[choice]
label = instruments[choice][0]
if sel.units == 0:
    st.success("No trade needed: the portfolio is already at the target beta.")
else:
    side = "Sell" if sel.units < 0 else "Buy"
    st.markdown(
        f"#### {side} {abs(sel.units):,} {label}  \n"
        + fmt.md(f"≈ {fmt.compact_money(abs(sel.notional))} of S&P 500 exposure")
    )
if "ES=F" in prices:
    st.caption(
        "Futures use the front-month continuous contract price from Yahoo (ES=F); "
        "check the contract you actually trade."
    )

# --- Before / after ---------------------------------------------------------------------
st.subheader(f"Before and after ({choice})")
w = v.weights
w_after = hedged_weights(w, sel.notional, nav)
cov = annualized_cov(snap.returns)
shocks = [-0.10, 0.10]


def pnl(beta: float, shock: float) -> float:
    return beta * nav * shock


compare = pd.DataFrame(
    {
        "Before": [
            pb,
            snap.dollar_beta,
            snap.portfolio_vol,
            v.net_exposure,
            v.gross_exposure,
            *[pnl(pb, s) for s in shocks],
        ],
        "After": [
            sel.post_beta,
            sel.post_beta * nav,
            hedged_vol(w, sel.notional, nav, cov),
            w_after.sum(),
            w_after.abs().sum(),
            *[pnl(sel.post_beta, s) for s in shocks],
        ],
    },
    index=[
        "Beta",
        "Dollar beta",
        "Volatility (ann.)",
        "Net exposure",
        "Gross exposure",
        "P&L if S&P −10%",
        "P&L if S&P +10%",
    ],
)
compare["Change"] = compare["After"] - compare["Before"]
formats = {
    "Beta": fmt.num,
    "Dollar beta": lambda x: fmt.money(x),
    "Volatility (ann.)": lambda x: fmt.pct(x, 1),
    "Net exposure": lambda x: fmt.pct(x, 1),
    "Gross exposure": lambda x: fmt.pct(x, 1),
    "P&L if S&P −10%": lambda x: fmt.money(x, signed=True),
    "P&L if S&P +10%": lambda x: fmt.money(x, signed=True),
}


def fmt_row(row: pd.Series) -> list[str]:
    f = formats[row.name]
    return [f(x) for x in row]


st.dataframe(
    compare.apply(fmt_row, axis=1, result_type="expand").set_axis(compare.columns, axis=1),
    width="stretch",
    row_height=28,
)
st.caption(
    "Gross and net exposure include the hedge position. Volatility uses the historical "
    "covariance of the risk window, with the hedge treated as SPY."
)

grid = pd.DataFrame(
    {
        "Unhedged": [pnl(pb, s) for s in DEFAULT_SHOCKS],
        "Hedged": [pnl(sel.post_beta, s) for s in DEFAULT_SHOCKS],
    },
    index=[fmt.pct(s, 1, signed=True) if s else "0%" for s in DEFAULT_SHOCKS],
).T
st.markdown("**Scenario P&L across S&P 500 moves**")
st.dataframe(
    grid.style.format(lambda x: fmt.money(x, signed=True)).map(fmt.pnl_color), width="stretch"
)
