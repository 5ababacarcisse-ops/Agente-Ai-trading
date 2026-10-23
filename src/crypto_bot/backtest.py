"""Small long-only moving-average backtest for research, not financial advice."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from crypto_bot.market_data import Candle


@dataclass(frozen=True)
class BacktestResult:
    initial_cash: float
    final_equity: float
    total_return_fraction: float
    max_drawdown_fraction: float
    trades: int
    candles_used: int


def sma(values: Sequence[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    output: list[float | None] = [None] * len(values)
    running_sum = 0.0
    for i, value in enumerate(values):
        running_sum += value
        if i >= window:
            running_sum -= values[i - window]
        if i >= window - 1:
            output[i] = running_sum / window
    return output


def backtest_sma_crossover(
    candles: Sequence[Candle],
    initial_cash: float = 400.0,
    fast_window: int = 10,
    slow_window: int = 30,
    fee_fraction: float = 0.001,
    slippage_fraction: float = 0.0005,
) -> BacktestResult:
    """Backtest a long-only SMA strategy with costs and no leverage.

    Signals are calculated from a candle close and used only for the following
    close-to-close return, avoiding use of future prices. Costs are charged on
    changes in position. This simplified model does not model spread, partial
    fills, tax, or market impact.
    """
    if initial_cash <= 0:
        raise ValueError("initial_cash must be > 0")
    if fast_window < 1 or slow_window <= fast_window:
        raise ValueError("require 1 <= fast_window < slow_window")
    if not 0 <= fee_fraction < 1 or not 0 <= slippage_fraction < 1:
        raise ValueError("fee and slippage must be in [0, 1)")
    if len(candles) < slow_window + 1:
        raise ValueError("not enough candles for the selected windows")
    closes = [float(c.close) for c in candles]
    if any(price <= 0 for price in closes):
        raise ValueError("all close prices must be positive")

    fast = sma(closes, fast_window)
    slow = sma(closes, slow_window)
    signals = [
        int(fast[i] is not None and slow[i] is not None and fast[i] > slow[i])
        for i in range(len(closes))
    ]

    equity = initial_cash
    peak = initial_cash
    max_drawdown = 0.0
    trades = 0
    cost_fraction = fee_fraction + slippage_fraction

    for i in range(1, len(closes)):
        position = signals[i - 1]
        previous_position = signals[i - 2] if i >= 2 else 0
        if position != previous_position:
            trades += 1
            equity *= 1.0 - cost_fraction
        market_return = closes[i] / closes[i - 1] - 1.0
        equity *= 1.0 + position * market_return
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)

    return BacktestResult(
        initial_cash=initial_cash,
        final_equity=equity,
        total_return_fraction=equity / initial_cash - 1.0,
        max_drawdown_fraction=max_drawdown,
        trades=trades,
        candles_used=len(candles),
    )
