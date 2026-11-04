"""Correlation structure of the holdings."""

from __future__ import annotations

import numpy as np
import pandas as pd


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation of daily returns over the common window."""
    return returns.corr()


def _upper_pairs(corr: pd.DataFrame) -> pd.Series:
    mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
    pairs = corr.where(mask).stack()
    pairs.index.names = ["a", "b"]
    return pairs


def average_pairwise_correlation(corr: pd.DataFrame) -> float:
    """Mean of the off-diagonal correlations: a quick read on how diversified the book is."""
    pairs = _upper_pairs(corr)
    return float(pairs.mean()) if len(pairs) else np.nan


def top_pairs(corr: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """The `n` most positively correlated pairs (columns a, b, corr)."""
    return _upper_pairs(corr).nlargest(n).rename("corr").reset_index()
