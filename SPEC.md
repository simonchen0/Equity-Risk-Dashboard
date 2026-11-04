# Equity Risk Dashboard — Spec

A desk-style equity risk dashboard: track a long/short stock portfolio, measure its market risk, stress it against S&P 500 moves, size an index hedge, and flag limit breaches.

**Stack:** Python 3.12 · Streamlit · pandas/numpy · Plotly · yfinance (free, delayed) · pydantic · pytest.
**Deploy target:** public Streamlit Community Cloud link with a demo portfolio; positions imported/exported as CSV (no database).

## Structure
- `src/riskdash/` — UI-free calculation engine (data providers, portfolio, analytics, alerts). No Streamlit imports, no network calls in tests.
- `app/` — Streamlit UI (`streamlit_app.py` entry point, `views/` pages, `components/` helpers). Pages only load → compute → render.
- `tests/` — offline unit tests on synthetic prices with hand-checked answers.

Run: `uv run streamlit run app/streamlit_app.py` · Test: `uv run pytest` · Lint: `uv run ruff check .`

## Features and status

**Foundation — Portfolio management** ✅ Done
Editable positions (long/short), cash balance, CSV import/export with row-level validation, $10M demo book. Market value, NAV, weights, gross/net exposure, day P&L, unrealized P&L.

**1. Risk analytics** ✅ Done
- ✅ Portfolio beta and dollar beta (raw or Blume-adjusted), per-position beta and R²
- ✅ Annualized portfolio and position volatility, per-position risk contribution
- ✅ Lookback selector (6M / 1Y / 2Y), weights and beta-adjusted exposure charts
- ✅ Risk page: correlation heatmap (grouped by sector), average pairwise correlation, top-5 most correlated pairs
- ✅ Risk page: sector exposure chart and table (long / short / net / gross, β contribution, share of risk)

**2. Scenario analysis** ✅ Done
Scenarios page: portfolio P&L across an S&P 500 shock grid (−20% to +20%, chart and table, in $ and % of NAV), plus a custom shock input with a per-position breakdown (biggest losses first).

**3. Hedging calculator** ✅ Done
Hedging page: enter a target beta (default 0, market-neutral) and pick SPY, ES or MES. Shows exact and whole-unit trade sizes for all three instruments, the beta left over from rounding, and a before/after comparison for the chosen hedge (beta, dollar beta, volatility, net/gross exposure, P&L for S&P ±10%) plus a hedged vs unhedged scenario table.

**4. Risk alerts** ✅ Done
Limits load from `config/default_limits.yaml` (validated; unknown keys are rejected) and can be edited per session on the Alerts page. Each rule reports OK, approaching (≥ 80% of the limit) or breach (over the limit); the Overview shows a banner and the Alerts page lists every rule:
- single-name weight > 10% (absolute weight, so shorts count)
- sector net weight > 30% (longs minus shorts)
- top-5 weights > 50%
- portfolio beta outside 0.00 to 1.00 (warning within 20% of the band's width from an edge)
- annualized volatility > 15%
- gross exposure > 150%, absolute net exposure > 100%
- pair correlation > 0.85, among positions of at least 3% of NAV

The default limits are illustrative, not recommendations.

**Remaining infrastructure:** GitHub Actions CI (ruff and pytest), a methodology note in the UI, a README with screenshots, and deployment.

## Financial calculation assumptions

| Item | Definition / assumption |
|---|---|
| Sign convention | Quantity > 0 = long, < 0 = short; short market value is negative |
| NAV | Cash + Σ (quantity × last price). Must be positive. |
| Weight | Market value / NAV; cash has zero weight in risk |
| Gross / Net exposure | (long MV + \|short MV\|) / NAV · (long MV + short MV) / NAV |
| Unrealized P&L | (last − avg cost) × quantity; positions without a cost basis are excluded |
| Day P&L | (last − previous close) × quantity, assuming no trades today; day return = day P&L / previous NAV |
| Prices | Daily split- and dividend-adjusted closes from Yahoo (delayed, may include today's intraday print). Day P&L on an ex-dividend date is therefore total-return. |
| Returns | Simple daily returns over one common date window for all holdings + SPY. A short price history shortens the window (a warning is shown); fewer than 60 observations is rejected. |
| Beta | OLS slope vs SPY: cov(rᵢ, r_SPY) / var(r_SPY). Raw returns (risk-free rate ignored at daily horizon). Blume adjusted = 0.67β + 0.33. |
| Portfolio beta | Σ wᵢ βᵢ; dollar beta = Σ MVᵢ βᵢ (P&L per 100% S&P move) |
| Volatility | Sample std × √252; portfolio vol = √(wᵀΣw) with current weights and annualized sample covariance |
| Risk contribution | wᵢ(Σw)ᵢ / wᵀΣw. Sums to 100%; negative means the position diversifies. |
| Correlation | Pearson correlation of daily returns over the same common window; average pairwise = mean of off-diagonal values |
| Sector exposure | Long = Σ positive weights, short = Σ negative weights, net = long + short, gross = Σ \|w\|. Sector = user override, otherwise Yahoo's sector, otherwise "Unclassified". |
| Scenarios | P&L_i = market value_i × beta_i × S&P move; total = dollar beta × move; % of NAV uses current NAV. A position with a missing beta makes the total NaN rather than understating it. Linear and systematic-only (no stock-specific or nonlinear effects). |
| Hedge sizing | Notional H = (β_target − β_portfolio) × NAV. SPY shares = H / P_SPY; ES = H / (F × $50); MES = H / (F × $5). Rounded to the nearest whole unit (halves away from zero). Hedge beta assumed 1. Hedged volatility treats the hedge as SPY in the historical covariance. ES price is Yahoo's front-month continuous contract (`ES=F`). Basis, carry, dividends and margin ignored. |

**Limitations:**
- yfinance is unofficial (rate limits, delays).
- Yahoo sectors are close to GICS but not the same.
- US equities in USD only.
- Betas and correlations are historical estimates, not forecasts, and are unstable over time (e.g. XOM's 1Y beta is currently negative).
- Cost basis is not split-adjusted.
- Not for live trading decisions.
