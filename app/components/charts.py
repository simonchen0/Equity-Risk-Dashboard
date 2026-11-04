"""Shared Plotly styling for the dark desk theme."""

from __future__ import annotations

import plotly.graph_objects as go

GRID = "rgba(138,155,163,0.12)"
AXIS = "#8a9ba3"
TEXT = "#d9e2e6"
# Diverging teal <-> red with a dark neutral midpoint: negative correlation is teal, positive red.
DIVERGING = [
    [0.0, "#1f8f83"],
    [0.25, "#2f6f6b"],
    [0.5, "#1c262d"],
    [0.75, "#a8485a"],
    [1.0, "#ed7088"],
]


def style(fig: go.Figure, height: int, pct_axis: str | None = "x") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=10, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=11),
        hoverlabel=dict(font=dict(family="monospace"), bgcolor="#151d23", bordercolor="#233039"),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=AXIS)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=AXIS)
    if pct_axis == "x":
        fig.update_xaxes(tickformat=".0%")
    return fig


CONFIG = {"displayModeBar": False}
