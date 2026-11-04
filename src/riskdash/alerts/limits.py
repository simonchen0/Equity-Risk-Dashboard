"""Configurable risk limits."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_LIMITS_PATH = Path(__file__).resolve().parents[3] / "config" / "default_limits.yaml"


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo in the YAML should fail loudly

    max_single_name_weight: float = Field(gt=0, le=1)
    max_sector_net_weight: float = Field(gt=0, le=1)
    max_top5_weight: float = Field(gt=0, le=1)
    beta_min: float
    beta_max: float
    max_volatility: float = Field(gt=0)
    max_gross_exposure: float = Field(gt=0)
    max_abs_net_exposure: float = Field(gt=0)
    max_pair_correlation: float = Field(gt=0, le=1)
    correlation_min_weight: float = Field(ge=0, le=1)
    warn_fraction: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def _beta_band(self) -> Limits:
        if self.beta_min >= self.beta_max:
            raise ValueError("beta_min must be below beta_max")
        return self


def load_limits(path: str | Path = DEFAULT_LIMITS_PATH) -> Limits:
    with open(path) as f:
        return Limits(**yaml.safe_load(f))
