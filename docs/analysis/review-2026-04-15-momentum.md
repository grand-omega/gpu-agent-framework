# Review: Momentum-Based Sector Rotation Strategy

Date: 2026-04-15
Plan: docs/plans/2026-04-15-momentum-sector-rotation.md

## Requirements checklist

- [x] **Criterion 1**: Script runs and prints Sharpe, CAGR, max drawdown for strategy and QQQM.
  Evidence: `uv run python src/momentum_backtest.py` completed successfully and printed:
  ```
  Sharpe Ratio    0.9171    0.7587
  Cagr            0.1925    0.1523
  Max Drawdown  -30.26%   -35.04%
  ```
- [x] **Criterion 2**: All tests pass.
  Evidence: 25 passed, 0 failed in 3.64s.
- [x] **Criterion 3**: Zero ruff violations.
  Evidence: `uv run ruff check .` output: "All checks passed!"
- [x] **Criterion 4**: Strategy uses 12-month lookback, top-3 selection, monthly rebalance.
  Evidence: `compute_momentum_signals` defaults `lookback_days=252, top_n=3` (line 52-55).
  Rebalance mask at line 73: `~prices.index.to_period("M").duplicated()`.
  `main()` calls with no overrides, so defaults are used (line 155).
- [x] **Criterion 5**: Transaction costs of 10 bps round-trip applied.
  Evidence: `DEFAULT_FEES = 0.0005` (line 29), passed to `vbt.Portfolio.from_orders(fees=fees)`
  at line 110. Per plan: vectorbt applies fees to both sides, so 0.0005 per side = 10 bps round-trip.
- [x] **Criterion 6**: Backtest covers 2018 to present.
  Evidence: `DEFAULT_START = "2018-01-01"` (line 28), `end=None` defaults to today (line 43).
- [x] **Criterion 7**: Code is under 300 lines per file.
  Evidence: `src/momentum_backtest.py` = 177 lines; `tests/test_momentum_backtest.py` = 148 lines.

## Code quality

- **Type hint coverage**: Complete on all public functions. Inner function `_extract` at line 131
  lacks type hints, but it is private/nested. Acceptable.
- **Test coverage**: 53% on `momentum_backtest.py`. Uncovered lines: 103-113 (`run_backtest`),
  131-141 (`compare_results`), 149-173 (`main`), 177 (`__main__` guard). The plan explicitly
  states "Do NOT test `run_backtest` with real data" and no requirement mandates coverage targets,
  so this is by design. The 10 pure-logic tests (compute_momentum_signals + download_data) all pass.
- **Ruff violations**: 0
- **Docstring coverage**: All public functions have Google-style docstrings. Inner `_extract`
  is undocumented but trivial.

## What worked well

- Clean separation of concerns: four pure functions plus `main()` matches plan exactly.
- The `compute_momentum_signals` function handles the warm-up period correctly at line 79:
  `if row.empty or len(row) < top_n: continue` skips early rebalance dates where returns are NaN.
- Test suite covers all meaningful logic paths for `compute_momentum_signals`: top-N selection,
  tie-breaking, non-rebalance NaN enforcement, weight sum, and early-window skipping.
- Mock-based tests for `download_data` correctly verify both single- and multi-ticker paths
  without network calls.
- Module-level constants (`SECTOR_ETFS`, `BENCHMARK_TICKER`, `DEFAULT_START`, `DEFAULT_FEES`)
  make configuration visible and testable.

## Issues found

None blocking. One minor observation:

- **Line 136-138** (`compare_results`): The `.iloc[0]` fallback for Series-shaped stats is
  defensive coding for potential vectorbt API differences. This is acceptable but untested;
  if vectorbt changes its return shape, this branch could silently return the wrong value.
  No fix required — just a known untested branch.

## Suggestions

- Consider adding a `--start` CLI argument to `main()` to make the date range configurable
  without editing source. Not required by the plan.
- The 53% coverage on `momentum_backtest.py` is acceptable given the plan's constraint against
  testing vectorbt portfolio construction with real data. A small synthetic vbt test fixture
  could improve this in a future cycle.

## Lessons learned

- Splitting pure signal-generation logic (`compute_momentum_signals`) from portfolio construction
  (`run_backtest`) makes the most important logic testable without heavy dependencies.
- The warm-up guard (`if row.empty or len(row) < top_n`) is the critical edge case — tested
  by `test_insufficient_lookback_skipped`.

## Verdict: APPROVED

All 7 success criteria met. Tests pass, no lint violations, script runs end-to-end.
