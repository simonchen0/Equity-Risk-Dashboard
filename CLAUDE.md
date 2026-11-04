
# Equity Risk Dashboard

## Project Overview
Build a professional equity risk and hedging dashboard inspired by tools used on institutional equity trading desks.

The application helps traders monitor portfolio performance, measure risk exposures, analyze market scenarios, and calculate hedges.

The goal is a functional, accurate, and visually polished project that demonstrates practical equity trading and risk management skills.

## Tech Stack
- Python 3.11+
- Streamlit for the web interface
- Pandas and NumPy for financial calculations
- Plotly for interactive charts
- yfinance for historical market data
- pytest for testing

Keep the stack simple. Avoid unnecessary frameworks, dependencies, and infrastructure.

## Core Features
1. Portfolio Management: Enter and edit stock positions, quantities, and purchase prices. Display portfolio values, weights, and P&L.
2. Risk Analytics: Calculate portfolio beta, volatility, correlations, and sector concentration.
3. Scenario Analysis: Estimate portfolio P&L under different S&P 500 market movements.
4. Hedging Calculator: Calculate SPY or index futures exposure required to achieve a target portfolio beta.
5. Risk Alerts: Flag exposures exceeding user-defined risk limits.

Build incrementally, starting with a functional MVP. Do not implement all features at once.

## Architecture
- Keep financial calculations separate from the UI.
- Separate market data retrieval from risk calculations.
- Organize code into logical, reusable modules.
- Avoid overengineering or introducing unnecessary abstractions.
- Maintain a clear, readable project structure.

## Financial Accuracy
- Prioritize correctness over visual appearance.
- Use established financial formulas and clearly document assumptions.
- Use adjusted historical prices when appropriate for return calculations.
- Handle missing data, invalid tickers, and insufficient price history.
- Distinguish daily P&L from total unrealized P&L.
- Clearly label estimates, historical metrics, and delayed data.
- Treat beta-based scenario analysis as an approximation, not a prediction.
- Write unit tests for financial calculations and edge cases.

## UI/UX
- Aim for a clean, professional institutional trading terminal aesthetic.
- Use a dark theme with clear information hierarchy.
- Prioritize useful financial information over decorative elements.
- Make charts interactive and metrics easy to understand.
- Display appropriate units, currencies, percentages, and dates.
- Keep navigation simple and intuitive.

## Development Workflow
- Before major features or architectural changes, propose a concise implementation plan for approval.
- Work on one feature at a time.
- Prefer simple, maintainable solutions.
- Reuse existing code rather than duplicating logic.
- Test changes and fix relevant failures before considering work complete.
- Do not add unrequested features or dependencies.
- Never commit, push, deploy, or perform destructive Git operations without permission.
- Never commit API keys, credentials, or secret files.

## Communication
- Explain important architectural decisions and financial calculations in simple terms.
- Keep explanations concise and practical.
- Flag unclear requirements rather than making significant assumptions.
- After implementing a feature, summarize what changed, what was tested, and what should come next.