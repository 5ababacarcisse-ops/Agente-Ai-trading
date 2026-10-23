"""Simple long-only moving-average signal generator."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from crypto_bot.backtest import sma


@dataclass(frozen=True)
class Signal:
    action: str  # "buy", "sell", or "hold"
    fast_average: float | None
    slow_average: float | None
    reason: str


def latest_signal(closes: Sequence[float], fast_window: int = 10, slow_window: int = 30) -> Signal:
    if fast_window < 1 or slow_window <= fast_window:
        raise ValueError("require 1 <= fast_window < slow_window")
    if len(closes) < slow_window + 1:
        raise ValueError("not enough closes for a crossover signal")
    if any(not isfinite(float(price)) or float(price) <= 0 for price in closes):
        raise ValueError("all closes must be finite and positive")
    fast = sma(closes, fast_window)
    slow = sma(closes, slow_window)
    i = len(closes) - 1
    prev = i - 1
    assert fast[i] is not None and slow[i] is not None
    assert fast[prev] is not None and slow[prev] is not None
    was_bullish = fast[prev] > slow[prev]
    is_bullish = fast[i] > slow[i]
    if not was_bullish and is_bullish:
        action, reason = "buy", "fast SMA crossed above slow SMA"
    elif was_bullish and not is_bullish:
        action, reason = "sell", "fast SMA crossed below slow SMA"
    else:
        action, reason = "hold", "no new crossover"
    return Signal(action, fast[i], slow[i], reason)
