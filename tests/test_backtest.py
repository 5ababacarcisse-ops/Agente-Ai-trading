from dataclasses import dataclass

import pytest

from crypto_bot.backtest import backtest_sma_crossover, sma


@dataclass
class FakeCandle:
    close: float


def candles(prices):
    return [FakeCandle(close=p) for p in prices]


def test_sma_returns_none_until_window_is_ready():
    assert sma([1, 2, 3, 4], 3) == [None, None, 2.0, 3.0]


def test_backtest_rejects_invalid_windows():
    with pytest.raises(ValueError):
        backtest_sma_crossover(candles(range(1, 40)), fast_window=10, slow_window=10)


def test_backtest_accounts_for_fees_and_returns_metrics():
    prices = [100 + i for i in range(40)]
    data = candles(prices)
    free = backtest_sma_crossover(
        data, initial_cash=400, fast_window=3, slow_window=8,
        fee_fraction=0, slippage_fraction=0,
    )
    with_costs = backtest_sma_crossover(
        data, initial_cash=400, fast_window=3, slow_window=8,
        fee_fraction=0.001, slippage_fraction=0.0005,
    )
    assert free.final_equity > 400
    assert with_costs.final_equity < free.final_equity
    assert with_costs.candles_used == len(data)
    assert with_costs.buy_hold_return_fraction == pytest.approx(prices[-1] / prices[0] - 1)
    assert 0 <= with_costs.max_drawdown_fraction <= 1
