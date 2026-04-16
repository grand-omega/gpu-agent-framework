"""Tests for momentum_backtest module."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from momentum_backtest import compute_momentum_signals, download_data


def _make_prices(n_days: int = 300, n_tickers: int = 5) -> pd.DataFrame:
    """Create synthetic price data with deterministic trends.

    Ticker_0 has the highest return, Ticker_1 second highest, etc.
    """
    dates = pd.bdate_range("2020-01-01", periods=n_days, freq="B")
    tickers = [f"T{i}" for i in range(n_tickers)]
    data = {}
    for i, t in enumerate(tickers):
        daily_return = 1.0 + 0.001 * (n_tickers - i)
        data[t] = 100.0 * np.cumprod(np.full(n_days, daily_return))
    return pd.DataFrame(data, index=dates)


class TestComputeMomentumSignals:
    """Tests for compute_momentum_signals."""

    def test_top_n_selection(self) -> None:
        """Top-N tickers by trailing return get equal weight."""
        prices = _make_prices(n_days=300, n_tickers=5)
        weights = compute_momentum_signals(prices, lookback_days=252, top_n=3)

        rebalance_rows = weights.dropna(how="all")
        assert len(rebalance_rows) > 0

        for _, row in rebalance_rows.iterrows():
            selected = row[row > 0]
            assert len(selected) == 3
            np.testing.assert_allclose(selected.values, 1.0 / 3)

    def test_top_tickers_are_highest_return(self) -> None:
        """The selected tickers should be those with highest trailing return."""
        prices = _make_prices(n_days=300, n_tickers=5)
        weights = compute_momentum_signals(prices, lookback_days=252, top_n=3)

        rebalance_rows = weights.dropna(how="all")
        for _, row in rebalance_rows.iterrows():
            selected = set(row[row > 0].index)
            assert selected == {"T0", "T1", "T2"}

    def test_non_rebalance_days_are_nan(self) -> None:
        """Non-rebalance rows should be all NaN."""
        prices = _make_prices(n_days=300, n_tickers=5)
        weights = compute_momentum_signals(prices, lookback_days=252, top_n=3)

        rebalance_mask = ~prices.index.to_period("M").duplicated()
        non_rebalance = weights.loc[~rebalance_mask]
        assert non_rebalance.isna().all().all()

    def test_unselected_tickers_are_zero(self) -> None:
        """Non-selected tickers on rebalance days should be 0."""
        prices = _make_prices(n_days=300, n_tickers=5)
        weights = compute_momentum_signals(prices, lookback_days=252, top_n=3)

        rebalance_rows = weights.dropna(how="all")
        for _, row in rebalance_rows.iterrows():
            zeros = row[row == 0]
            assert len(zeros) == 2

    def test_weights_sum_to_one(self) -> None:
        """Weights on rebalance days should sum to 1.0."""
        prices = _make_prices(n_days=300, n_tickers=5)
        weights = compute_momentum_signals(prices, lookback_days=252, top_n=3)

        rebalance_rows = weights.dropna(how="all")
        for _, row in rebalance_rows.iterrows():
            np.testing.assert_allclose(row.sum(), 1.0)

    def test_ties_handled(self) -> None:
        """When all sectors have equal return, top_n are still selected."""
        dates = pd.bdate_range("2020-01-01", periods=300, freq="B")
        flat = pd.DataFrame(
            {f"T{i}": np.cumprod(np.full(300, 1.001)) * 100 for i in range(5)},
            index=dates,
        )
        weights = compute_momentum_signals(flat, lookback_days=252, top_n=3)
        rebalance_rows = weights.dropna(how="all")
        for _, row in rebalance_rows.iterrows():
            selected = row[row > 0]
            assert len(selected) == 3

    def test_insufficient_lookback_skipped(self) -> None:
        """Rebalance dates before lookback window is filled produce no weights."""
        prices = _make_prices(n_days=260, n_tickers=5)
        weights = compute_momentum_signals(prices, lookback_days=252, top_n=3)

        first_rebalance_mask = ~prices.index.to_period("M").duplicated()
        first_dates = prices.index[first_rebalance_mask]
        early = first_dates[first_dates < prices.index[252]]
        for d in early:
            assert weights.loc[d].isna().all()


class TestDownloadData:
    """Tests for download_data with mocked yfinance."""

    def test_single_ticker(self) -> None:
        """Single ticker download returns a DataFrame with that column."""
        dates = pd.bdate_range("2023-01-01", periods=10)
        mock_df = pd.DataFrame({"Close": np.arange(10, dtype=float)}, index=dates)

        with patch("momentum_backtest.yf.download", return_value=mock_df):
            result = download_data(["AAPL"], start="2023-01-01")

        assert "AAPL" in result.columns
        assert len(result) == 10

    def test_multiple_tickers(self) -> None:
        """Multiple ticker download returns correct columns."""
        dates = pd.bdate_range("2023-01-01", periods=10)
        arrays = [["Close", "Close"], ["AAPL", "MSFT"]]
        cols = pd.MultiIndex.from_arrays(arrays, names=["Price", "Ticker"])
        mock_df = pd.DataFrame(
            np.random.default_rng(42).random((10, 2)),
            index=dates,
            columns=cols,
        )

        with patch("momentum_backtest.yf.download", return_value=mock_df):
            result = download_data(["AAPL", "MSFT"], start="2023-01-01")

        assert set(result.columns) == {"AAPL", "MSFT"}

    def test_nan_columns_dropped(self) -> None:
        """Columns that are all NaN should be dropped."""
        dates = pd.bdate_range("2023-01-01", periods=10)
        arrays = [["Close", "Close"], ["AAPL", "BAD"]]
        cols = pd.MultiIndex.from_arrays(arrays, names=["Price", "Ticker"])
        data = np.column_stack([np.arange(10, dtype=float), np.full(10, np.nan)])
        mock_df = pd.DataFrame(data, index=dates, columns=cols)

        with patch("momentum_backtest.yf.download", return_value=mock_df):
            result = download_data(["AAPL", "BAD"], start="2023-01-01")

        assert "BAD" not in result.columns
        assert "AAPL" in result.columns
