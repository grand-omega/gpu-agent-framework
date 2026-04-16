# Plan: Momentum-Based Sector Rotation Strategy

Date: 2026-04-15
Status: Draft

## Problem statement

Build a momentum-based sector rotation backtest that each month selects the
top 3 sector ETFs by trailing 12-month return, equal-weights them, and
compares performance against a buy-and-hold QQQM baseline. The strategy
should account for realistic transaction costs (10 bps round-trip).

## Research findings

### vectorbt (v0.28.5)

- `Portfolio.from_orders()` supports multi-asset rebalancing via
  `size_type='targetpercent'` with `cash_sharing=True` and
  `call_seq='auto'` (sells before buys).
- Monthly rebalance mask: `~price.index.to_period('M').duplicated()`
  identifies first trading day of each month.
- Fees are passed as a fraction (e.g., `fees=0.001` for 10 bps).
- `Portfolio.from_holding(close)` creates a buy-and-hold baseline.
- Stats available: `pf.sharpe_ratio()`, `pf.annualized_return()`,
  `pf.max_drawdown()`, `pf.stats()`.
- Requires Python >= 3.10; works with Python 3.12.

### yfinance

- `yf.download(tickers, start, end)` downloads OHLCV for multiple tickers.
- Returns MultiIndex columns `(Price, Ticker)` when multiple tickers given.
- Access close prices: `data['Close']` returns DataFrame with ticker columns.

### numpy compatibility

- vectorbt 0.28.5 does not pin numpy<2 in its metadata, but internally
  uses numba which may constrain numpy. If installation fails, pin
  `numpy<2.0` as a fallback.

## Dependencies needed

```bash
uv add vectorbt yfinance
```

If numpy compatibility issues arise:

```bash
uv add "numpy<2.0"
```

## Approach

Single-module design in `src/momentum_backtest.py` with four pure functions
plus a `main()` entry point:

1. **`download_data(tickers, start, end)`** -- wraps `yf.download`, returns
   a DataFrame of adjusted close prices indexed by date with ticker columns.

2. **`compute_momentum_signals(prices, lookback, top_n)`** -- computes
   trailing `lookback`-month returns, ranks sectors each month, returns a
   boolean DataFrame (True = selected) and a weights DataFrame (1/top_n for
   selected, 0 otherwise).

3. **`run_backtest(prices, weights, fees)`** -- builds a
   `vbt.Portfolio.from_orders()` with `size_type='targetpercent'`,
   `cash_sharing=True`, `call_seq='auto'`, and the given fees. Returns the
   portfolio object.

4. **`compare_results(strategy_pf, benchmark_pf)`** -- extracts Sharpe
   ratio, CAGR (annualized return), and max drawdown from both portfolios.
   Returns a dict or prints a formatted comparison table.

5. **`main()`** -- orchestrates the above: downloads data, generates
   signals, runs strategy backtest, runs QQQM buy-and-hold benchmark,
   prints comparison to stdout.

### Key implementation details

- **Momentum calculation**: For each rebalance date (first trading day of
  month), compute the return over the prior 252 trading days (approx 12
  months). Use `prices.pct_change(252)`.
- **Rebalance mask**: `~prices.index.to_period('M').duplicated()` gives
  True on the first trading day of each month.
- **Weight matrix**: Create a DataFrame of same shape as sector prices,
  filled with `np.nan`. On rebalance days, set top-3 sectors to `1/3` and
  others to `0`. Non-rebalance rows stay `np.nan` (vectorbt holds previous
  allocation).
- **Transaction costs**: `fees=0.0005` per side = 10 bps round-trip (vectorbt
  applies fees to both entry and exit, so half per side).
- **Benchmark**: `vbt.Portfolio.from_holding(qqqm_prices)` for buy-and-hold.
- **Date range**: 2018-01-01 to present. The first 12 months are warm-up
  for the momentum lookback, so effective backtest starts ~2019-01.

## Task breakdown

### Task 1: Create src/momentum_backtest.py with data download function

- Create `src/momentum_backtest.py`
- Implement `download_data(tickers: list[str], start: str, end: str) -> pd.DataFrame`
- Should call `yf.download()`, extract Close prices, drop any columns with
  all NaN, return clean DataFrame
- Add proper type hints and docstrings

### Task 2: Implement momentum signal generation

- Add `compute_momentum_signals(prices: pd.DataFrame, lookback_days: int = 252, top_n: int = 3) -> pd.DataFrame`
- Compute trailing returns via `pct_change(lookback_days)`
- On each rebalance date (first of month), rank sectors, pick top N
- Return weights DataFrame: 1/top_n for selected, 0 for others, NaN for
  non-rebalance rows

### Task 3: Implement backtest execution and comparison

- Add `run_backtest(prices: pd.DataFrame, weights: pd.DataFrame, fees: float = 0.0005) -> vbt.Portfolio`
- Uses `vbt.Portfolio.from_orders()` with `size_type='targetpercent'`,
  `group_by=True`, `cash_sharing=True`, `call_seq='auto'`
- Add `compare_results(strategy_pf, benchmark_pf) -> dict`
- Extract sharpe_ratio, annualized_return, max_drawdown from each

### Task 4: Implement main() and CLI entry point

- Add `main()` that wires everything together
- Define sector ETF tickers and QQQM
- Download data, compute signals, run backtests, print comparison
- Guard with `if __name__ == "__main__"`
- Verify it runs: `uv run python src/momentum_backtest.py`

### Task 5: Write tests in tests/test_momentum_backtest.py

- Test `compute_momentum_signals` with synthetic price data:
  - Known prices where ranking is deterministic
  - Verify top 3 get weight 1/3, others get 0
  - Verify NaN on non-rebalance days
- Test edge cases:
  - All sectors have same return (tie-breaking)
  - Missing data / NaN handling
- Mock `yf.download` to test `download_data` without network
- Do NOT test `run_backtest` with real data -- mock or use tiny synthetic data

### Task 6: Integration test and lint

- Run `uv run pytest` -- all tests pass
- Run `uv run ruff check .` -- no violations
- Run `uv run ruff format .` -- formatted
- Run `uv run python src/momentum_backtest.py` -- verify stdout output

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| vectorbt + numpy 2.0 incompatibility | Pin `numpy<2.0` if needed |
| yfinance rate limiting or data gaps | Add retry logic; handle NaN gracefully |
| vectorbt API changes in 0.28.x | Pin version: `uv add vectorbt==0.28.5` |
| Warm-up period reduces backtest length | Document that first 12 months are lookback |
| group_by parameter syntax | Use `group_by=True` to treat all columns as one group |

## Success criteria

1. Script runs via `uv run python src/momentum_backtest.py` and prints
   Sharpe ratio, CAGR, and max drawdown for both strategy and QQQM
2. All tests pass with `uv run pytest`
3. Zero ruff violations
4. Strategy uses 12-month lookback, top-3 selection, monthly rebalance
5. Transaction costs of 10 bps round-trip are applied
6. Backtest covers 2018 to present
7. Code is under 300 lines per file
