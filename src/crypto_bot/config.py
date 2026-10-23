"""Environment-based configuration with live trading disabled by default."""
from __future__ import annotations

import os
from dataclasses import dataclass


LIVE_CONFIRMATION = "I_UNDERSTAND_REAL_MONEY_RISK"


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class BotConfig:
    mode: str = "paper"
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    candles: int = 300
    fast_window: int = 10
    slow_window: int = 30
    max_allocation_fraction: float = 0.10
    max_daily_loss_fraction: float = 0.01
    fee_fraction: float = 0.001
    slippage_fraction: float = 0.0005
    poll_seconds: int = 60
    live_enabled: bool = False
    api_key: str = ""
    api_secret: str = ""
    live_confirmation: str = ""

    @classmethod
    def from_env(cls) -> "BotConfig":
        return cls(
            mode=os.getenv("TRADING_MODE", "paper").strip().lower(),
            symbol=os.getenv("TRADING_SYMBOL", "BTCUSDT").strip().upper(),
            interval=os.getenv("TRADING_INTERVAL", "1h").strip(),
            candles=int(os.getenv("TRADING_CANDLES", "300")),
            fast_window=int(os.getenv("FAST_WINDOW", "10")),
            slow_window=int(os.getenv("SLOW_WINDOW", "30")),
            max_allocation_fraction=float(os.getenv("MAX_ALLOCATION_FRACTION", "0.10")),
            max_daily_loss_fraction=float(os.getenv("MAX_DAILY_LOSS_FRACTION", "0.01")),
            fee_fraction=float(os.getenv("FEE_FRACTION", "0.001")),
            slippage_fraction=float(os.getenv("SLIPPAGE_FRACTION", "0.0005")),
            poll_seconds=int(os.getenv("POLL_SECONDS", "60")),
            live_enabled=_bool_env("LIVE_TRADING_ENABLED", False),
            api_key=os.getenv("BINANCE_API_KEY", ""),
            api_secret=os.getenv("BINANCE_API_SECRET", ""),
            live_confirmation=os.getenv("LIVE_TRADING_CONFIRMATION", ""),
        )

    def validate(self) -> None:
        if self.mode not in {"paper", "live"}:
            raise ValueError("TRADING_MODE must be 'paper' or 'live'")
        if not self.symbol.isalnum() or not self.symbol:
            raise ValueError("TRADING_SYMBOL must contain only letters and numbers")
        if self.fast_window < 1 or self.slow_window <= self.fast_window:
            raise ValueError("require 1 <= FAST_WINDOW < SLOW_WINDOW")
        if self.candles < self.slow_window + 2 or self.candles > 1000:
            raise ValueError("TRADING_CANDLES must be between SLOW_WINDOW + 2 and 1000")
        if not 0 < self.max_allocation_fraction <= 0.10:
            raise ValueError("MAX_ALLOCATION_FRACTION must be in (0, 0.10]")
        if not 0 < self.max_daily_loss_fraction <= 0.01:
            raise ValueError("MAX_DAILY_LOSS_FRACTION must be in (0, 0.01]")
        if not 0 <= self.fee_fraction < 0.05 or not 0 <= self.slippage_fraction < 0.05:
            raise ValueError("fee/slippage assumptions must be in [0, 0.05)")
        if self.poll_seconds < 10:
            raise ValueError("POLL_SECONDS must be at least 10")
        if self.mode == "live":
            if self.symbol not in {"BTCUSDT", "ETHUSDT"}:
                raise ValueError("Initial live release is restricted to BTCUSDT or ETHUSDT")
            if not self.live_enabled:
                raise ValueError("Live trading blocked: set LIVE_TRADING_ENABLED=true only after reviewing the code")
            if self.live_confirmation != LIVE_CONFIRMATION:
                raise ValueError("Live trading blocked: LIVE_TRADING_CONFIRMATION is missing or incorrect")
            if not self.api_key or not self.api_secret:
                raise ValueError("Live trading requires BINANCE_API_KEY and BINANCE_API_SECRET")
