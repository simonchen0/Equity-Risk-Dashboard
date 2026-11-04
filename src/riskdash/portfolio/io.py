"""CSV import/export.

Format: columns `ticker, quantity, avg_cost, sector` (avg_cost and sector optional).
The cash balance is a row with ticker `CASH` and the amount in `quantity`.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import IO

import pandas as pd
from pydantic import ValidationError

from riskdash.portfolio.models import Portfolio, Position

COLUMNS = ["ticker", "quantity", "avg_cost", "sector"]


class PortfolioImportError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _clean(value: object) -> object:
    return None if pd.isna(value) or value == "" else value


def portfolio_from_frame(df: pd.DataFrame) -> Portfolio:
    df = df.rename(columns=lambda c: str(c).strip().lower())
    missing = {"ticker", "quantity"} - set(df.columns)
    if missing:
        raise PortfolioImportError([f"missing required column(s): {', '.join(sorted(missing))}"])

    errors: list[str] = []
    positions: list[Position] = []
    cash = 0.0
    for i, row in enumerate(df.to_dict("records"), start=2):  # row 1 is the header
        ticker = _clean(row.get("ticker"))
        if ticker is None:
            continue  # tolerate blank lines / empty editor rows
        try:
            qty = float(row.get("quantity"))
            if not math.isfinite(qty):
                raise ValueError("not finite")
        except (TypeError, ValueError):
            errors.append(f"row {i}: quantity {row.get('quantity')!r} is not a number")
            continue
        if str(ticker).strip().upper() == "CASH":
            cash += qty
            continue
        try:
            avg_cost = _clean(row.get("avg_cost"))
            positions.append(
                Position(
                    ticker=str(ticker),
                    quantity=qty,
                    avg_cost=float(avg_cost) if avg_cost is not None else None,
                    sector=_clean(row.get("sector")),
                )
            )
        except (ValidationError, ValueError) as exc:
            msg = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
            errors.append(f"row {i} ({ticker}): {msg}")
    if errors:
        raise PortfolioImportError(errors)
    try:
        return Portfolio(positions=positions, cash=cash)
    except ValidationError as exc:
        raise PortfolioImportError([e["msg"] for e in exc.errors()]) from exc


def read_portfolio_csv(source: str | Path | IO) -> Portfolio:
    try:
        df = pd.read_csv(source)
    except Exception as exc:
        raise PortfolioImportError([f"could not parse CSV: {exc}"]) from exc
    return portfolio_from_frame(df)


def portfolio_to_frame(portfolio: Portfolio) -> pd.DataFrame:
    rows = [p.model_dump() for p in portfolio.positions]
    rows.append({"ticker": "CASH", "quantity": portfolio.cash, "avg_cost": None, "sector": None})
    return pd.DataFrame(rows, columns=COLUMNS)


def portfolio_to_csv(portfolio: Portfolio) -> str:
    buf = io.StringIO()
    portfolio_to_frame(portfolio).to_csv(buf, index=False)
    return buf.getvalue()
