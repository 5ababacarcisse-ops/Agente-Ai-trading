"""Persistent state for the bot's own live position and daily risk guard.

This file is local runtime state, not a source of truth for exchange balances.
Back it up securely and do not commit it.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path


@dataclass
class LiveState:
    owned_quantity: float = 0.0
    last_signal_candle: int = 0
    day_utc: str = ""
    day_start_equity: float = 0.0
    halted: bool = False
    pending_order: str = ""


class LiveStateStore:
    def __init__(self, path: str = "data/live_state.json"):
        self.path = Path(path)
        self.state = self._load()

    def _load(self) -> LiveState:
        if not self.path.exists():
            return LiveState()
        try:
            state = LiveState(**json.loads(self.path.read_text(encoding="utf-8")))
            if (not isfinite(state.owned_quantity) or state.owned_quantity < 0
                    or not isfinite(state.day_start_equity) or state.day_start_equity < 0
                    or state.last_signal_candle < 0 or not isinstance(state.pending_order, str)
                    or not isinstance(state.halted, bool) or not isinstance(state.day_utc, str)):
                raise ValueError("invalid values in live state")
            return state
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Live state is unreadable; refusing to trade: {exc}") from exc

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(asdict(self.state), indent=2), encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def roll_day(self, equity: float) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if self.state.day_utc != today:
            self.state.day_utc = today
            self.state.day_start_equity = equity
            self.state.halted = False
            self.save()
