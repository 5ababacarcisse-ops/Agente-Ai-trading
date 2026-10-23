"""Defence-in-depth gates for any live Spot order."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from crypto_bot.config import BotConfig


@dataclass(frozen=True)
class OrderDecision:
    allowed: bool
    reason: str
    quote_amount: float = 0.0


def validate_live_order(
    config: BotConfig,
    *,
    side: str,
    symbol: str,
    current_equity: float,
    free_quote_balance: float,
    day_start_equity: float,
    last_price: float,
    daily_loss_fraction: float | None = None,
) -> OrderDecision:
    """Fail closed. This function does not place an order."""
    if config.mode != "live" or not config.live_enabled:
        return OrderDecision(False, "live mode is not enabled")
    if config.live_confirmation != "I_UNDERSTAND_REAL_MONEY_RISK":
        return OrderDecision(False, "live confirmation missing")
    if side not in {"BUY", "SELL"}:
        return OrderDecision(False, "unsupported side")
    if symbol != config.symbol:
        return OrderDecision(False, "symbol mismatch")
    numeric_values = (current_equity, free_quote_balance, day_start_equity, last_price)
    if any(not isfinite(value) for value in numeric_values):
        return OrderDecision(False, "non-finite balance or price")
    if min(current_equity, free_quote_balance, day_start_equity) < 0 or last_price <= 0:
        return OrderDecision(False, "invalid balance or price")
    loss_fraction = (
        max(0.0, (day_start_equity - current_equity) / day_start_equity)
        if day_start_equity > 0 else 1.0
    )
    threshold = daily_loss_fraction if daily_loss_fraction is not None else config.max_daily_loss_fraction
    if not isfinite(threshold) or not 0 < threshold <= 0.01:
        return OrderDecision(False, "invalid daily loss threshold")
    if loss_fraction >= threshold:
        return OrderDecision(False, "daily loss threshold reached")
    if side == "BUY":
        amount = min(current_equity * config.max_allocation_fraction, free_quote_balance)
        if amount <= 10:
            return OrderDecision(False, "buy amount is too small or no free quote balance")
        return OrderDecision(True, "within configured allocation cap", amount)
    return OrderDecision(True, "sell requires caller to provide only bot-owned base quantity")
