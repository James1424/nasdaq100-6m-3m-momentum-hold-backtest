from __future__ import annotations

import pandas as pd

from config import (
    BACKTEST_START,
    COMPONENT_CHANGES_FILE,
    CURRENT_TICKERS_FILE,
    HOLDING_MONTHS,
    MOMENTUM_WINDOWS,
    OUTPUT_DIR,
    PRICE_FILE,
    SIX_MONTH_DETAIL_FILE,
    SIX_MONTH_SUMMARY_FILE,
    THREE_MONTH_DETAIL_FILE,
    THREE_MONTH_SUMMARY_FILE,
    TOP_NS,
)


def clean_ticker(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper().replace(".", "-")
    return text if text and text not in {"NAN", "NONE", "—", "-"} else None


def get_month_start_prices(daily_prices: pd.DataFrame) -> pd.DataFrame:
    """Use the first available trading day of each month as the monthly anchor."""
    daily_prices = daily_prices.sort_index()
    groups = daily_prices.groupby(daily_prices.index.to_period("M"))
    first_rows = []
    first_dates = []

    for _, group in groups:
        if group.empty:
            continue
        first_rows.append(group.iloc[0])
        first_dates.append(group.index[0])

    month_start_prices = pd.DataFrame(first_rows, index=pd.DatetimeIndex(first_dates))
    month_start_prices.index.name = "decision_date"
    return month_start_prices


def compute_momentum(month_start_prices: pd.DataFrame, window: int) -> pd.DataFrame:
    """Momentum = average of the previous N one-month returns.

    No extra shift is applied. At a month-start decision date, the latest completed
    month-start-to-month-start return is included, matching this project's original timing.
    """
    monthly_returns = month_start_prices.pct_change(fill_method=None)
    return monthly_returns.rolling(window=window, min_periods=window).mean()


def load_current_tickers() -> set[str]:
    df = pd.read_csv(CURRENT_TICKERS_FILE)
    if "ticker" not in df.columns:
        raise ValueError(f"{CURRENT_TICKERS_FILE} must have column: ticker")
    return {t for t in df["ticker"].map(clean_ticker).dropna().tolist() if t}


def load_component_changes() -> pd.DataFrame:
    df = pd.read_csv(COMPONENT_CHANGES_FILE)
    if df.empty:
        return pd.DataFrame(columns=["date", "added_ticker", "removed_ticker"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["added_ticker"] = df.get("added_ticker", pd.Series(index=df.index, dtype=object)).map(clean_ticker)
    df["removed_ticker"] = df.get("removed_ticker", pd.Series(index=df.index, dtype=object)).map(clean_ticker)
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def universe_as_of(decision_date: pd.Timestamp, current_tickers: set[str], changes: pd.DataFrame) -> set[str]:
    """Reconstruct Nasdaq-100 constituents effective at decision_date.

    Start from today's current list and reverse every component change whose date
    is after the decision date. A change on or before the decision date is already
    known and should remain reflected in the current-forward timeline.
    """
    membership = set(current_tickers)
    if changes.empty:
        return membership

    future_changes = changes[changes["date"] > decision_date].sort_values("date", ascending=False)
    for _, row in future_changes.iterrows():
        added = clean_ticker(row.get("added_ticker"))
        removed = clean_ticker(row.get("removed_ticker"))
        # Reverse a future change: later additions were not present yet;
        # later removals were still present then.
        if added:
            membership.discard(added)
        if removed:
            membership.add(removed)
    return membership


def run_window_backtest(
    month_start_prices: pd.DataFrame,
    current_tickers: set[str],
    changes: pd.DataFrame,
    window: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    momentum = compute_momentum(month_start_prices, window)
    backtest_start = pd.Timestamp(BACKTEST_START)

    rows: list[dict] = []
    dates = list(month_start_prices.index)
    date_to_pos = {d: i for i, d in enumerate(dates)}

    for decision_date in dates:
        if decision_date < backtest_start:
            continue

        raw_universe = universe_as_of(decision_date, current_tickers, changes)
        universe = sorted(t for t in raw_universe if t in momentum.columns)
        if not universe:
            continue

        price_row = month_start_prices.loc[decision_date]
        valid = [t for t in universe if pd.notna(price_row.get(t, pd.NA))]
        if not valid:
            continue

        # Key fix: rank only stocks that were Nasdaq-100 members at this decision date.
        mom_row = momentum.loc[decision_date, valid].dropna().sort_values(ascending=False)
        if mom_row.empty:
            continue

        pos = date_to_pos[decision_date]

        for top_n in TOP_NS:
            selected = mom_row.head(top_n)
            if len(selected) < top_n:
                continue

            selected_tickers = selected.index.tolist()
            selected_mom = selected.values.tolist()
            avg_momentum = float(selected.mean())

            for hold_m in HOLDING_MONTHS:
                sell_pos = pos + hold_m
                if sell_pos >= len(dates):
                    continue

                sell_date = dates[sell_pos]
                buy_prices = month_start_prices.loc[decision_date, selected_tickers]
                sell_prices = month_start_prices.loc[sell_date, selected_tickers]
                stock_returns = (sell_prices / buy_prices - 1).dropna()

                # Require all selected stocks to have a valid holding-period return.
                if len(stock_returns) < top_n:
                    continue

                row = {
                    "decision_month": decision_date.strftime("%Y-%m"),
                    "decision_date": decision_date.strftime("%Y-%m-%d"),
                    "sell_date": sell_date.strftime("%Y-%m-%d"),
                    "universe_asof_date": decision_date.strftime("%Y-%m-%d"),
                    "raw_universe_size": len(raw_universe),
                    "available_universe_size": len(valid),
                    "momentum_window": window,
                    "holding_months": hold_m,
                    "top_n": top_n,
                    "stock_1": selected_tickers[0] if top_n >= 1 else "",
                    "mom_1": selected_mom[0] if top_n >= 1 else pd.NA,
                    "stock_1_return": stock_returns.get(selected_tickers[0], pd.NA) if top_n >= 1 else pd.NA,
                    "stock_2": selected_tickers[1] if top_n >= 2 else "",
                    "mom_2": selected_mom[1] if top_n >= 2 else pd.NA,
                    "stock_2_return": stock_returns.get(selected_tickers[1], pd.NA) if top_n >= 2 else pd.NA,
                    "stock_3": selected_tickers[2] if top_n >= 3 else "",
                    "mom_3": selected_mom[2] if top_n >= 3 else pd.NA,
                    "stock_3_return": stock_returns.get(selected_tickers[2], pd.NA) if top_n >= 3 else pd.NA,
                    "avg_momentum": avg_momentum,
                    "holding_return": float(stock_returns.mean()),
                }
                rows.append(row)

    detail = pd.DataFrame(rows)
    if detail.empty:
        raise RuntimeError(f"No backtest results for {window}-month momentum window.")

    summary = (
        detail.groupby(["momentum_window", "top_n", "holding_months"], as_index=False)
        .agg(
            trades=("holding_return", "count"),
            avg_return=("holding_return", "mean"),
            median_return=("holding_return", "median"),
            win_rate=("holding_return", lambda x: (x > 0).mean()),
            best_return=("holding_return", "max"),
            worst_return=("holding_return", "min"),
            avg_available_universe_size=("available_universe_size", "mean"),
        )
        .sort_values(["momentum_window", "top_n", "holding_months"])
    )

    return detail, summary


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    daily_prices = pd.read_csv(PRICE_FILE, index_col="date", parse_dates=True).sort_index()
    month_start_prices = get_month_start_prices(daily_prices)
    current_tickers = load_current_tickers()
    changes = load_component_changes()

    for window in MOMENTUM_WINDOWS:
        detail, summary = run_window_backtest(month_start_prices, current_tickers, changes, window)
        if window == 6:
            detail.to_csv(SIX_MONTH_DETAIL_FILE, index=False)
            summary.to_csv(SIX_MONTH_SUMMARY_FILE, index=False)
            print(f"Saved {SIX_MONTH_DETAIL_FILE}")
            print(f"Saved {SIX_MONTH_SUMMARY_FILE}")
        elif window == 3:
            detail.to_csv(THREE_MONTH_DETAIL_FILE, index=False)
            summary.to_csv(THREE_MONTH_SUMMARY_FILE, index=False)
            print(f"Saved {THREE_MONTH_DETAIL_FILE}")
            print(f"Saved {THREE_MONTH_SUMMARY_FILE}")


if __name__ == "__main__":
    main()
