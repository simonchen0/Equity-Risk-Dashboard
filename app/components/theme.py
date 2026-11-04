"""Shared look and feel: global CSS and the few layout helpers every page uses.

Colours live in `components.format` (so charts and tables agree) and in
`.streamlit/config.toml` (the Streamlit theme). The CSS only handles density and borders.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from typing import Any

import streamlit as st

from components import format as fmt

ROW_H = 28  # dataframe row height in px


def table_height(n_rows: int, max_rows: int | None = None) -> int:
    """Pixel height that fits `n_rows` plus the header (capped at `max_rows` rows)."""
    n = n_rows if max_rows is None else min(n_rows, max_rows)
    return ROW_H * n + 40  # 40 = header row plus borders


_CSS = f"""
<style>
  [data-testid="stMainBlockContainer"] {{
      padding: 4.25rem 1.5rem 2rem; max-width: 1500px;
  }}
  [data-testid="stHeader"] {{ background: {fmt.BG}; border-bottom: 1px solid {fmt.BORDER}; }}
  [data-testid="stAppDeployButton"], [data-testid="stDecoration"] {{ display: none; }}

  /* Page title and section headings */
  h1 {{ font-size: 1.3rem !important; font-weight: 600; padding: 0.25rem 0 0.25rem; }}
  h3 {{
      font-size: 0.78rem !important; font-weight: 600; letter-spacing: .06em;
      text-transform: uppercase; color: {fmt.MUTED};
      border-bottom: 1px solid {fmt.BORDER}; padding: 0.75rem 0 0.35rem !important;
      margin-bottom: 0.5rem;
  }}
  [data-testid="stCaptionContainer"] {{ color: {fmt.MUTED}; }}

  /* Metrics: small uppercase label, tabular numerals */
  [data-testid="stMetricLabel"] p {{
      font-size: 0.72rem; text-transform: uppercase; letter-spacing: .05em; color: {fmt.MUTED};
  }}
  [data-testid="stMetricValue"] {{
      font-size: 1.35rem; font-variant-numeric: tabular-nums; font-weight: 500;
  }}
  [data-testid="stMetricDelta"] {{ font-size: 0.78rem; }}

  /* KPI strip: one bordered panel with vertical dividers */
  [class*="st-key-kpi"] [data-testid="stColumn"] + [data-testid="stColumn"] {{
      border-left: 1px solid {fmt.BORDER}; padding-left: 1rem;
  }}

  /* Status line under the top bar */
  .status-line {{
      display: flex; gap: .6rem; align-items: baseline; flex-wrap: wrap;
      padding: .45rem .75rem; margin-bottom: .5rem; font-size: .85rem;
      border: 1px solid {fmt.BORDER}; border-radius: 4px; background: {fmt.PANEL};
  }}
  .status-line .dot {{ font-size: .7rem; }}
  .status-line .detail {{ color: {fmt.MUTED}; }}

  /* Control strip and footer */
  .control-label {{
      color: {fmt.MUTED}; font-size: .72rem; text-transform: uppercase;
      letter-spacing: .05em; white-space: nowrap;
  }}
  .footer-note {{ color: {fmt.MUTED}; font-size: .75rem; margin-top: 1.5rem; }}
</style>
"""


def inject_css() -> None:
    st.html(_CSS)


def kpi_strip(items: Sequence[dict[str, Any]], key: str) -> None:
    """One bordered strip of metrics. Each item holds `st.metric` keyword arguments."""
    with st.container(border=True, key=f"kpi_{key}"):
        for col, item in zip(st.columns(len(items)), items, strict=True):
            col.metric(**item)


def status_line(alerts: Sequence[Any]) -> None:
    """Compact limit status: counts, then the messages of anything breached or approaching."""
    breaches = [a for a in alerts if a.severity == "breach"]
    warns = [a for a in alerts if a.severity == "warn"]
    parts = []
    if breaches:
        n = len(breaches)
        parts.append(
            f'<span class="dot" style="color:{fmt.NEG}">●</span> '
            f"<b>{n} breach{'es' if n > 1 else ''}</b>"
        )
    if warns:
        parts.append(
            f'<span class="dot" style="color:{fmt.WARN}">●</span> <b>{len(warns)} approaching</b>'
        )
    if not parts:
        parts.append(f'<span class="dot" style="color:{fmt.POS}">●</span> <b>All limits clear</b>')
    detail = " · ".join(escape(a.message) for a in [*breaches, *warns])
    st.html(
        f'<div class="status-line">{"&nbsp;&nbsp;&nbsp;".join(parts)}'
        + (f'<span class="detail">{detail}</span>' if detail else "")
        + "</div>"
    )
