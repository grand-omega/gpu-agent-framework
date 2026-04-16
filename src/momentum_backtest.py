"""Momentum-based sector rotation backtest.

Downloads sector ETF data, computes trailing 12-month momentum signals,
selects top-N sectors monthly, and compares against a QQQM benchmark.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import vectorbt as vbt
import yfinance as yf

SECTOR_ETFS: list[str] = [
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLI",
    "XLC",
    "XLY",
    "XLP",
    "XLB",
    "XLRE",
    "XLU",
]
BENCHMARK_TICKER: str = "QQQM"
DEFAULT_START: str = "2018-01-01"
DEFAULT_FEES: float = 0.0005


def download_data(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """Download adjusted close prices for the given tickers.

    Args:
        tickers: List of ticker symbols to download.
        start: Start date string (YYYY-MM-DD).
        end: Optional end date string. Defaults to today.

    Returns:
        DataFrame indexed by date with one column per ticker (Close prices).
    """
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]})
    prices = prices.dropna(how="all", axis=1)
    return prices


def compute_momentum_signals(
    prices: pd.DataFrame,
    lookback_days: int = 252,
    top_n: int = 3,
) -> pd.DataFrame:
    """Compute momentum-based allocation weights.

    On each rebalance date (first trading day of the month), ranks sectors
    by trailing return over *lookback_days* and assigns equal weight to the
    top *top_n* sectors. Non-rebalance rows are NaN (hold previous weights).

    Args:
        prices: DataFrame of close prices (date index, ticker columns).
        lookback_days: Number of trading days for the trailing return window.
        top_n: Number of top sectors to select each month.

    Returns:
        DataFrame of target weights, same shape as *prices*.
    """
    returns = prices.pct_change(lookback_days)

    rebalance_mask = ~prices.index.to_period("M").duplicated()

    weights = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)

    for date in prices.index[rebalance_mask]:
        row = returns.loc[date].dropna()
        if row.empty or len(row) < top_n:
            continue
        top_tickers = row.nlargest(top_n).index
        weights.loc[date] = 0.0
        weights.loc[date, top_tickers] = 1.0 / top_n

    return weights


def run_backtest(
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    fees: float = DEFAULT_FEES,
) -> vbt.Portfolio:
    """Run a portfolio backtest using vectorbt.

    Args:
        prices: DataFrame of close prices.
        weights: DataFrame of target percentage weights (NaN = hold).
        fees: Transaction fee per side as a decimal fraction.

    Returns:
        A vectorbt Portfolio object.
    """
    portfolio = vbt.Portfolio.from_orders(
        close=prices,
        size=weights,
        size_type="targetpercent",
        group_by=True,
        cash_sharing=True,
        call_seq="auto",
        fees=fees,
        freq="1D",
    )
    return portfolio


def compare_results(
    strategy_pf: vbt.Portfolio,
    benchmark_pf: vbt.Portfolio,
) -> dict[str, dict[str, float]]:
    """Extract and compare key metrics from two portfolios.

    Args:
        strategy_pf: The momentum strategy portfolio.
        benchmark_pf: The benchmark (buy-and-hold) portfolio.

    Returns:
        Dict with 'strategy' and 'benchmark' sub-dicts containing
        sharpe_ratio, cagr, and max_drawdown.
    """

    def _extract(pf: vbt.Portfolio) -> dict[str, float]:
        sr = pf.sharpe_ratio()
        ar = pf.annualized_return()
        md = pf.max_drawdown()
        return {
            "sharpe_ratio": float(sr.iloc[0] if isinstance(sr, pd.Series) else sr),
            "cagr": float(ar.iloc[0] if isinstance(ar, pd.Series) else ar),
            "max_drawdown": float(md.iloc[0] if isinstance(md, pd.Series) else md),
        }

    return {
        "strategy": _extract(strategy_pf),
        "benchmark": _extract(benchmark_pf),
    }


def main() -> None:
    """Run the momentum sector rotation backtest and print results."""
    all_tickers = [*SECTOR_ETFS, BENCHMARK_TICKER]
    prices = download_data(all_tickers, start=DEFAULT_START)

    sector_prices = prices[SECTOR_ETFS]
    benchmark_prices = prices[[BENCHMARK_TICKER]]

    weights = compute_momentum_signals(sector_prices)

    strategy_pf = run_backtest(sector_prices, weights)
    benchmark_pf = vbt.Portfolio.from_holding(benchmark_prices, freq="1D")

    results = compare_results(strategy_pf, benchmark_pf)

    print("\n=== Momentum Sector Rotation vs QQQM Buy-and-Hold ===\n")
    print(f"{'Metric':<20} {'Strategy':>12} {'Benchmark':>12}")
    print("-" * 46)
    for metric in ["sharpe_ratio", "cagr", "max_drawdown"]:
        s_val = results["strategy"][metric]
        b_val = results["benchmark"][metric]
        label = metric.replace("_", " ").title()
        if metric == "max_drawdown":
            print(f"{label:<20} {s_val:>11.2%} {b_val:>12.2%}")
        else:
            print(f"{label:<20} {s_val:>12.4f} {b_val:>12.4f}")
    print()


if __name__ == "__main__":
    main()
