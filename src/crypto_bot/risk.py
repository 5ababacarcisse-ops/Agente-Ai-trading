"""Small, deterministic risk helpers for research and paper trading."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    max_allocation_fraction: float = 0.25
    risk_per_trade_fraction: float = 0.005
    max_daily_loss_fraction: float = 0.01

    def validate(self) -> None:
        for name, value in (
            ("max_allocation_fraction", self.max_allocation_fraction),
            ("risk_per_trade_fraction", self.risk_per_trade_fraction),
            ("max_daily_loss_fraction", self.max_daily_loss_fraction),
        ):
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")


def max_allocated_capital(equity: float, config: RiskConfig) -> float:
    """Return the maximum notional allocation; does not imply a safe loss limit."""
    config.validate()
    if equity < 0:
        raise ValueError("equity cannot be negative")
    return equity * config.max_allocation_fraction


def risk_budget(equity: float, config: RiskConfig) -> float:
    """Return a theoretical risk budget; real losses may exceed this amount."""
    config.validate()
    if equity < 0:
        raise ValueError("equity cannot be negative")
    return equity * config.risk_per_trade_fraction


def daily_loss_limit(equity_at_day_start: float, config: RiskConfig) -> float:
    """Return the configured daily loss threshold in quote currency."""
    config.validate()
    if equity_at_day_start < 0:
        raise ValueError("equity cannot be negative")
    return equity_at_day_start * config.max_daily_loss_fraction
