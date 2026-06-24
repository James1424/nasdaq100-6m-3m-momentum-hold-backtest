from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from config import (
    README_FILE,
    SIX_MONTH_DETAIL_FILE,
    SIX_MONTH_SUMMARY_FILE,
    THREE_MONTH_DETAIL_FILE,
    THREE_MONTH_SUMMARY_FILE,
    TOP_NS,
)


def fmt_pct(x) -> str:
    if pd.isna(x):
        return ""
    return f"{float(x):.2%}"


def fmt_num(x) -> str:
    if pd.isna(x):
        return ""
    return f"{float(x):.1f}"


def fmt_detail_table(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Format the monthly detail table for one Top-N strategy.

    The README is intentionally split into Top 1 / Top 2 / Top 3 tables so that
    each table only shows the stock columns that are actually used.
    """
    out = df[df["top_n"] == top_n].copy()

    pct_cols = [
        "mom_1",
        "mom_2",
        "mom_3",
        "avg_momentum",
        "holding_return",
        "stock_1_return",
        "stock_2_return",
        "stock_3_return",
    ]
    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].map(fmt_pct)

    base_cols = [
        "decision_month",
        "decision_date",
        "sell_date",
        "holding_months",
        "available_universe_size",
        "stock_1",
        "mom_1",
        "stock_1_return",
    ]

    if top_n >= 2:
        base_cols.extend(["stock_2", "mom_2", "stock_2_return"])
    if top_n >= 3:
        base_cols.extend(["stock_3", "mom_3", "stock_3_return"])

    base_cols.extend(["avg_momentum", "holding_return"])
    out = out[[c for c in base_cols if c in out.columns]]

    out = out.rename(
        columns={
            "decision_month": "Decision Month",
            "decision_date": "Decision Date",
            "sell_date": "Sell Date",
            "holding_months": "Holding Months",
            "available_universe_size": "Universe Size",
            "stock_1": "Stock 1",
            "mom_1": "Mom 1",
            "stock_1_return": "Stock 1 Return",
            "stock_2": "Stock 2",
            "mom_2": "Mom 2",
            "stock_2_return": "Stock 2 Return",
            "stock_3": "Stock 3",
            "mom_3": "Mom 3",
            "stock_3_return": "Stock 3 Return",
            "avg_momentum": "Avg Momentum",
            "holding_return": "Holding Return",
        }
    )
    return out


def non_overlapping_compounded_return(sub: pd.DataFrame, holding_months: int) -> float:
    """Compound only non-overlapping trades starting from January."""
    if sub.empty:
        return float("nan")

    selected_months = list(range(1, 13, holding_months))
    selected = sub[sub["decision_date"].dt.month.isin(selected_months)].copy()
    selected = selected.sort_values("decision_date")

    if selected.empty:
        return float("nan")

    return float((1 + selected["holding_return"]).prod() - 1)


def fmt_annual_return_table(detail: pd.DataFrame) -> pd.DataFrame:
    """Build a year-by-year non-overlapping compounded return table."""
    if detail.empty:
        return pd.DataFrame()

    df = detail.copy()
    df["decision_date"] = pd.to_datetime(df["decision_date"])
    df["year"] = df["decision_date"].dt.year

    years = sorted(df["year"].dropna().unique())
    current_year = datetime.now().year
    rows: list[dict] = []

    for year in years:
        year_df = df[df["year"] == year].copy()
        year_label = f"{int(year)} (YTD)" if int(year) == current_year else str(int(year))
        row: dict[str, object] = {"Year": year_label}

        for top_n in TOP_NS:
            for hold_m in sorted(df["holding_months"].dropna().unique()):
                sub = year_df[
                    (year_df["top_n"] == top_n)
                    & (year_df["holding_months"] == hold_m)
                ].copy()
                value = non_overlapping_compounded_return(sub, int(hold_m))
                row[f"Top {top_n} Hold {int(hold_m)}M"] = fmt_pct(value)

        rows.append(row)

    return pd.DataFrame(rows)


def fmt_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    pct_cols = ["avg_return", "median_return", "win_rate", "best_return", "worst_return"]
    for col in pct_cols:
        out[col] = out[col].map(fmt_pct)
    if "avg_available_universe_size" in out.columns:
        out["avg_available_universe_size"] = out["avg_available_universe_size"].map(fmt_num)

    out = out.rename(
        columns={
            "momentum_window": "Momentum Window",
            "top_n": "Top N",
            "holding_months": "Holding Months",
            "trades": "Trades",
            "avg_return": "Avg Return",
            "median_return": "Median Return",
            "win_rate": "Win Rate",
            "best_return": "Best Return",
            "worst_return": "Worst Return",
            "avg_available_universe_size": "Avg Universe Size",
        }
    )
    return out


def to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data available._"
    return df.to_markdown(index=False)


def build_top_n_sections(detail: pd.DataFrame, title: str) -> str:
    parts: list[str] = []
    for top_n in TOP_NS:
        top_df = fmt_detail_table(detail, top_n=top_n)
        parts.append(
            f"""
### {title} - Top {top_n}

Each row is one monthly decision under the Top {top_n} version of this momentum strategy. The same selected stock basket is evaluated with 1, 2, and 3 month holding periods. `Universe Size` is the available point-in-time Nasdaq-100 universe after filtering for valid prices at that decision date.

{to_markdown(top_df)}
""".strip()
        )
    return "\n\n".join(parts)


def build_section(title: str, detail_file, summary_file) -> str:
    detail = pd.read_csv(detail_file)
    summary = pd.read_csv(summary_file)

    annual_return_md = to_markdown(fmt_annual_return_table(detail))
    summary_md = to_markdown(fmt_summary_table(summary))
    top_sections = build_top_n_sections(detail, title)

    return f"""
## {title}

The monthly detail results are split into three tables: Top 1, Top 2, and Top 3. This keeps the README readable while still showing every monthly decision from 2016 to the latest available completed holding period.

### {title} Yearly Compounded Returns

The table below uses non-overlapping compounding paths starting from January. Hold 1M compounds monthly decisions Jan through Dec, Hold 2M compounds Jan/Mar/May/Jul/Sep/Nov decisions, and Hold 3M compounds Jan/Apr/Jul/Oct decisions. The current year is labelled YTD when it is incomplete.

{annual_return_md}

### {title} Summary

{summary_md}

{top_sections}
""".strip()


def main() -> None:
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    six_section = build_section(
        "Six-Month Momentum Strategy Monthly Backtest",
        SIX_MONTH_DETAIL_FILE,
        SIX_MONTH_SUMMARY_FILE,
    )
    three_section = build_section(
        "Three-Month Momentum Strategy Monthly Backtest",
        THREE_MONTH_DETAIL_FILE,
        THREE_MONTH_SUMMARY_FILE,
    )

    readme = f"""# Nasdaq-100 Momentum Strategy Comparison

This project compares Nasdaq-100 momentum strategies using two separate momentum windows:

- Six-month average momentum
- Three-month average momentum

For each momentum window, the project tests:

- Top 1 / Top 2 / Top 3 selected stocks
- 1 / 2 / 3 month holding periods
- Monthly decisions from 2016 to the latest available data

The README is automatically regenerated from the CSV outputs. For each momentum window, the README first shows yearly compounded returns, then the summary table, and then the Top 1 / Top 2 / Top 3 monthly backtest tables.

Last updated: **{updated_at}**

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

{six_section}

{three_section}
"""

    README_FILE.write_text(readme, encoding="utf-8")
    print(f"Updated {README_FILE}")


if __name__ == "__main__":
    main()
