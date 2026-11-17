import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from components import format as fmt  # noqa: E402


@pytest.mark.parametrize("fn", [fmt.money, fmt.compact_money, fmt.pct, fmt.num])
@pytest.mark.parametrize("bad", [None, float("nan")])
def test_missing_values_show_a_dash(fn, bad):
    assert fn(bad) == "—"


def test_money():
    assert fmt.money(1234.4) == "$1,234"
    assert fmt.money(-1234.4) == "-$1,234"
    assert fmt.money(1234.4, signed=True) == "+$1,234"
    assert fmt.money(12.346, decimals=2) == "$12.35"


def test_compact_money_tiers_and_sign():
    assert fmt.compact_money(999) == "$999"
    assert fmt.compact_money(1_500) == "$1.50K"
    assert fmt.compact_money(2_500_000, signed=True) == "+$2.50M"
    assert fmt.compact_money(-3_200_000_000) == "-$3.20B"


@pytest.mark.parametrize("x", [-0.4, 0.4, 0.0])
def test_tiny_amounts_never_show_a_negative_zero(x):
    assert fmt.money(x) == "$0"
    assert fmt.compact_money(x, signed=True) == "$0"


def test_pct_and_num_never_show_negative_zero():
    assert fmt.pct(0.0123, 1) == "1.2%"
    assert fmt.pct(0.0123, 1, signed=True) == "+1.2%"
    assert fmt.pct(-0.000001) == "0.00%"
    assert fmt.pct(-0.000001, signed=True) == "0.00%"
    assert fmt.num(-0.0001) == "0.00"
    assert fmt.num(1234.567) == "1,234.57"


def test_md_escapes_dollars_and_pnl_color():
    assert fmt.md("$1M and $2M") == "\\$1M and \\$2M"
    assert fmt.pnl_color(5) == f"color: {fmt.POS}"
    assert fmt.pnl_color(-5) == f"color: {fmt.NEG}"
    assert fmt.pnl_color(0) == fmt.pnl_color(None) == f"color: {fmt.NEUTRAL}"
