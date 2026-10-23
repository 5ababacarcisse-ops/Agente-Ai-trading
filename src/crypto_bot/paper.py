"""Local paper portfolio; state file must never contain API credentials."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path


@dataclass
class PaperState:
    cash: float = 400.0
    base_quantity: float = 0.0
    last_action: str = "none"
    last_signal_candle: int = 0
    day_utc: str = ""
    day_start_equity: float = 400.0
    halted: bool = False


class PaperPortfolio:
    def __init__(self, path: str = "data/paper_state.json", initial_cash: float = 400.0):
        self.path = Path(path)
        self.initial_cash = initial_cash
        self.state = self._load()

    def _load(self) -> PaperState:
        if not self.path.exists():
            return PaperState(cash=self.initial_cash, day_start_equity=self.initial_cash)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            state = PaperState(**data)
            numeric_values = (state.cash, state.base_quantity, state.day_start_equity)
            if (any(not isfinite(value) for value in numeric_values)
                    or state.cash < 0 or state.base_quantity < 0 or state.day_start_equity < 0
                    or state.last_signal_candle < 0 or not isinstance(state.halted, bool)):
                raise ValueError("invalid values in paper state")
            return state
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Paper state is unreadable; refusing to reset it silently: {exc}") from exc

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(self.state), indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def equity(self, price: float) -> float:
        return self.state.cash + self.state.base_quantity * price

    def roll_day(self, price: float) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.state.day_utc != today:
            self.state.day_utc = today
            self.state.day_start_equity = self.equity(price)
            self.state.halted = False
            self.save()

    def buy(self, price: float, quote_amount: float, fee_fraction: float, candle_id: int) -> None:
        if self.state.base_quantity > 0 or quote_amount <= 0 or price <= 0:
            return
        amount = min(quote_amount, self.state.cash)
        cost = amount * (1 + fee_fraction)
        if cost > self.state.cash:
            amount = self.state.cash / (1 + fee_fraction)
            cost = self.state.cash
        self.state.cash -= cost
        self.state.base_quantity = amount / price
        self.state.last_action = "buy"
        self.state.last_signal_candle = candle_id
        self.save()

    def sell(self, price: float, fee_fraction: float, candle_id: int) -> None:
        if self.state.base_quantity <= 0 or price <= 0:
            return
        proceeds = self.state.base_quantity * price * (1 - fee_fraction)
        self.state.cash += proceeds
        self.state.base_quantity = 0.0
        self.state.last_action = "sell"
        self.state.last_signal_candle = candle_id
        self.save()
