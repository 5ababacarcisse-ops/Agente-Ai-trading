import pytest

from crypto_bot.config import BotConfig, LIVE_CONFIRMATION
from crypto_bot.live_guard import validate_live_order


def test_paper_mode_is_default(monkeypatch):
    monkeypatch.delenv("TRADING_MODE", raising=False)
    monkeypatch.delenv("LIVE_TRADING_ENABLED", raising=False)
    config = BotConfig.from_env()
    assert config.mode == "paper"
    assert not config.live_enabled


def test_live_mode_fails_closed_without_explicit_enable():
    config = BotConfig(mode="live", live_enabled=False, api_key="k", api_secret="s",
                       live_confirmation=LIVE_CONFIRMATION)
    with pytest.raises(ValueError, match="LIVE_TRADING_ENABLED"):
        config.validate()


def test_live_mode_requires_confirmation():
    config = BotConfig(mode="live", live_enabled=True, api_key="k", api_secret="s")
    with pytest.raises(ValueError, match="CONFIRMATION"):
        config.validate()


def test_order_guard_blocks_paper_mode():
    config = BotConfig()
    decision = validate_live_order(
        config, side="BUY", symbol="BTCUSDT", current_equity=400,
        free_quote_balance=400, day_start_equity=400, last_price=100,
    )
    assert not decision.allowed


def test_order_guard_enforces_daily_loss():
    config = BotConfig(mode="live", live_enabled=True, api_key="k", api_secret="s",
                       live_confirmation=LIVE_CONFIRMATION)
    decision = validate_live_order(
        config, side="BUY", symbol="BTCUSDT", current_equity=390,
        free_quote_balance=390, day_start_equity=400, last_price=100,
    )
    assert not decision.allowed
