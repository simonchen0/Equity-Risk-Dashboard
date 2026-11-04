import plotly.graph_objects as go
import streamlit as st
from components import format as fmt
from components.charts import CONFIG, DIVERGING, TEXT, style
from components.state import require_snapshot, sector_map

from riskdash.analytics.correlation import (
    average_pairwise_correlation,
    correlation_matrix,
    top_pairs,
)
from riskdash.analytics.exposure import sector_exposure

st.title("Risk")
snap = require_snapshot()
pos = snap.positions
sectors = sector_map(list(pos.index))

# --- Sector exposure --------------------------------------------------------------------
st.subheader(
    "Sector exposure",
    help="Weights as % of NAV. Sector = your override if set, otherwise Yahoo's classification "
    "(close to, but not identical to, GICS).",
)
exp = sector_exposure(pos["weight"], sectors, snap.betas, snap.risk_contrib)

left, right = st.columns([1, 1])
with left:
    s = exp.sort_values("gross")  # Plotly draws bottom-up: largest gross at the top
    fig = go.Figure(
        [
            go.Bar(
                name="Long",
                y=s.index,
                x=s["long"],
                orientation="h",
                marker_color=fmt.POS,
                hovertemplate="%{y}<br>Long %{x:.1%}<extra></extra>",
            ),
            go.Bar(
                name="Short",
                y=s.index,
                x=s["short"],
                orientation="h",
                marker_color=fmt.NEG,
                hovertemplate="%{y}<br>Short %{x:.1%}<extra></extra>",
            ),
            go.Scatter(
                name="Net",
                y=s.index,
                x=s["net"],
                mode="markers",
                marker=dict(
                    symbol="diamond", size=10, color=TEXT, line=dict(width=2, color="#0b0f14")
                ),
                hovertemplate="%{y}<br>Net %{x:.1%}<extra></extra>",
            ),
        ]
    )
    style(fig, height=34 * len(s) + 70)
    fig.update_layout(
        barmode="relative",
        bargap=0.35,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    )
    st.plotly_chart(fig, width="stretch", config=CONFIG)

with right:
    table = exp[["long", "short", "net", "gross", "beta_adj", "risk_contrib", "positions"]]
    st.dataframe(
        table.style.format(
            {
                "long": lambda x: fmt.pct(x, 1),
                "short": lambda x: fmt.pct(x, 1),
                "net": lambda x: fmt.pct(x, 1),
                "gross": lambda x: fmt.pct(x, 1),
                "beta_adj": fmt.num,
                "risk_contrib": lambda x: fmt.pct(x, 1),
                "positions": "{:d}",
            },
            na_rep="—",
        ),
        width="stretch",
        height=35 * (len(table) + 1) + 3,
        column_config={
            "_index": st.column_config.Column("Sector", pinned=True),
            "long": "Long",
            "short": "Short",
            "net": "Net",
            "gross": "Gross",
            "beta_adj": st.column_config.Column(
                "β contrib", help="Σ weight × beta: the sector's share of portfolio beta."
            ),
            "risk_contrib": st.column_config.Column(
                "Risk %", help="Sector's share of portfolio variance (sums to 100%)."
            ),
            "positions": "#",
        },
    )

# --- Correlation ------------------------------------------------------------------------
st.subheader(
    "Correlation",
    help="Pearson correlation of daily returns over the risk window. Historical estimate, "
    "not a forecast; correlations tend to rise in sell-offs.",
)
# Group names by sector (largest gross first), then by position size, so blocks are visible.
order = sorted(
    pos.index,
    key=lambda t: (list(exp.index).index(sectors[t]), -abs(pos.loc[t, "weight"])),
)
corr = correlation_matrix(snap.returns[order])

left, right = st.columns([3, 1])
with left:
    fig = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=order,
            y=order,
            zmin=-1,
            zmax=1,
            colorscale=DIVERGING,
            texttemplate="%{z:.2f}",
            textfont=dict(size=10),
            hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>",
            colorbar=dict(thickness=10, tickvals=[-1, -0.5, 0, 0.5, 1]),
            xgap=2,
            ygap=2,
        )
    )
    style(fig, height=max(320, 30 * len(order) + 60), pct_axis=None)
    fig.update_xaxes(side="top", tickfont=dict(family="monospace"), showgrid=False)
    fig.update_yaxes(autorange="reversed", tickfont=dict(family="monospace"), showgrid=False)
    st.plotly_chart(fig, width="stretch", config=CONFIG)

with right:
    st.metric(
        "Avg pairwise correlation",
        fmt.num(average_pairwise_correlation(corr)),
        border=True,
        help="Mean of all off-diagonal correlations. Higher = less diversification.",
    )
    st.markdown("**Most correlated pairs**")
    pairs = top_pairs(corr, n=5)
    pairs["pair"] = pairs["a"] + " / " + pairs["b"]
    st.dataframe(
        pairs[["pair", "corr"]].style.format({"corr": fmt.num}),
        hide_index=True,
        width="stretch",
        column_config={"pair": "Pair", "corr": "ρ"},
    )
