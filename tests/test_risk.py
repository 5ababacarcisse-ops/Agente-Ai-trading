import pytest

from crypto_bot.risk import (
    RiskConfig,
    daily_loss_limit,
    max_allocated_capital,
    risk_budget,
)


def test_example_limits_for_400_euro_equity():
    config = RiskConfig()
    assert max_allocated_capital(400, config) == pytest.approx(100)
    assert risk_budget(400, config) == pytest.approx(2)
    assert daily_loss_limit(400, config) == pytest.approx(4)


def test_negative_equity_is_rejected():
    with pytest.raises(ValueError):
        max_allocated_capital(-1, RiskConfig())


def test_invalid_fraction_is_rejected():
    with pytest.raises(ValueError):
        RiskConfig(max_allocation_fraction=0).validate()
