"""Number formatting conventions for the UI (desk style: $ with separators, signed P&L)."""

from __future__ import annotations

import math

POS, NEG, NEUTRAL = "#26a269", "#e5534b", "#8b949e"


def _bad(x: float | None) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def money(x: float | None, decimals: int = 0, signed: bool = False) -> str:
    if _bad(x):
        return "—"
    sign = "+" if signed and x > 0 else "-" if x < 0 else ""
    return f"{sign}${abs(x):,.{decimals}f}"


def compact_money(x: float | None, signed: bool = False) -> str:
    if _bad(x):
        return "—"
    sign = "+" if signed and x > 0 else "-" if x < 0 else ""
    a = abs(x)
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{sign}${a / div:,.2f}{suffix}"
    return f"{sign}${a:,.0f}"


def pct(x: float | None, decimals: int = 2, signed: bool = False) -> str:
    if _bad(x):
        return "—"
    return f"{x * 100:+.{decimals}f}%" if signed else f"{x * 100:.{decimals}f}%"


def num(x: float | None, decimals: int = 2) -> str:
    return "—" if _bad(x) else f"{x:,.{decimals}f}"


def md(text: str) -> str:
    """Escape `$` so Streamlit markdown doesn't render dollar amounts as LaTeX."""
    return text.replace("$", "\\$")


def pnl_color(x: float | None) -> str:
    if _bad(x) or x == 0:
        return f"color: {NEUTRAL}"
    return f"color: {POS}" if x > 0 else f"color: {NEG}"
