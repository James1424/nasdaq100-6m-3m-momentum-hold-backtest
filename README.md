# Nasdaq-100 Momentum Strategy Comparison

This project compares Nasdaq-100 momentum strategies using two separate momentum windows:

- Six-month average momentum
- Three-month average momentum

For each momentum window, the project tests:

- Top 1 / Top 2 / Top 3 selected stocks
- 1 / 2 / 3 month holding periods
- Monthly decisions from 2016 to the latest available data

The README is automatically regenerated from the CSV outputs. For each momentum window, the README first shows yearly compounded returns, then the summary table, and then the Top 1 / Top 2 / Top 3 monthly backtest tables.

## Method

- Stock universe: point-in-time Nasdaq-100 constituents reconstructed from the current constituent list plus historical component additions/removals
- Decision date: first trading day of each month
- Momentum definition: average of the previous N one-month returns based on month-start adjusted close prices
- Ranking rule: at each decision date, rank only stocks that were Nasdaq-100 constituents as of that decision date and have valid price data
- Buy price: adjusted close on the decision date
- Sell price: adjusted close on the first trading day after the selected holding period
- Portfolio return: equal-weighted average return of the selected stocks

## Run Locally

```bash
pip install -r requirements.txt
python run_all.py
```

## Outputs

- `data/nasdaq100_current_tickers.csv`
- `data/nasdaq100_component_changes.csv`
- `data/nasdaq100_all_historical_tickers.csv`
- `data/nasdaq100_prices.csv`
- `output/six_month_detail.csv`
- `output/six_month_summary.csv`
- `output/three_month_detail.csv`
- `output/three_month_summary.csv`

Run `python run_all.py` to download data, run the point-in-time backtest, and regenerate this README with the full result tables.
