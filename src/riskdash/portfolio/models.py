"""Portfolio domain model.

Sign convention: quantity > 0 is long, quantity < 0 is short. Cash is held separately and
can be negative (margin borrowing). NAV = cash + sum of signed market values.
"""

from __future__ import annotations

import math
import re

from pydantic import BaseModel, Field, field_validator, model_validator

TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


class Position(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float | None = Field(default=None, gt=0)
    sector: str | None = None  # manual override of the vendor sector

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not TICKER_RE.match(v):
            raise ValueError(f"invalid ticker {v!r}")
        if v == "CASH":
            raise ValueError("CASH is reserved for the cash balance")
        return v

    @field_validator("quantity")
    @classmethod
    def _nonzero(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("quantity must be a finite number")
        if v == 0:
            raise ValueError("quantity must be non-zero (positive = long, negative = short)")
        return v

    @field_validator("sector")
    @classmethod
    def _blank_sector_is_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip() or None


class Portfolio(BaseModel):
    positions: list[Position] = Field(default_factory=list)
    cash: float = Field(default=0.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def _unique_tickers(self) -> Portfolio:
        seen: set[str] = set()
        dupes = {p.ticker for p in self.positions if p.ticker in seen or seen.add(p.ticker)}
        if dupes:
            raise ValueError(f"duplicate tickers: {', '.join(sorted(dupes))}")
        return self

    @property
    def tickers(self) -> list[str]:
        return [p.ticker for p in self.positions]
