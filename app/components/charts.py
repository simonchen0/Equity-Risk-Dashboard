"""Shared Plotly styling for the dark desk theme."""

from __future__ import annotations

import plotly.graph_objects as go

GRID = "rgba(139,148,158,0.2)"
AXIS = "#8b949e"
TEXT = "#e6edf3"
# Diverging blue <-> red with a neutral dark-gray midpoint (dataviz reference palette, dark mode)
DIVERGING = [
    [0.0, "#1c5cab"],
    [0.25, "#3987e5"],
    [0.5, "#383835"],
    [0.75, "#e66767"],
    [1.0, "#b8302f"],
]


def style(fig: go.Figure, height: int, pct_axis: str | None = "x") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=10, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        hoverlabel=dict(font=dict(family="monospace")),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=AXIS)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=AXIS)
    if pct_axis == "x":
        fig.update_xaxes(tickformat=".0%")
    return fig


CONFIG = {"displayModeBar": False}
