import pytest

from crypto_bot.config import BotConfig, LIVE_CONFIRMATION, MAINNET_CONFIRMATION
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


def test_live_mode_restricts_symbols():
    config = BotConfig(mode="live", symbol="DOGEUSDT", live_enabled=True,
                       api_key="k", api_secret="s", live_confirmation=LIVE_CONFIRMATION)
    with pytest.raises(ValueError, match="BTCUSDT or ETHUSDT"):
        config.validate()


def test_allocation_cap_is_ten_percent():
    config = BotConfig(max_allocation_fraction=0.11)
    with pytest.raises(ValueError, match="0.10"):
        config.validate()


def test_testnet_is_enabled_by_default():
    config = BotConfig()
    assert config.testnet is True



def test_mainnet_requires_separate_confirmation():
    config = BotConfig(mode="live", live_enabled=True, testnet=False,
                       api_key="k", api_secret="s",
                       live_confirmation=LIVE_CONFIRMATION)
    with pytest.raises(ValueError, match="MAINNET_TRADING_CONFIRMATION"):
        config.validate()


def test_mainnet_accepts_only_exact_confirmation():
    config = BotConfig(mode="live", live_enabled=True, testnet=False,
                       api_key="k", api_secret="s",
                       live_confirmation=LIVE_CONFIRMATION,
                       mainnet_confirmation=MAINNET_CONFIRMATION)
    config.validate()


def test_order_guard_rejects_nonfinite_balance():
    config = BotConfig(mode="live", live_enabled=True, api_key="k", api_secret="s",
                       live_confirmation=LIVE_CONFIRMATION)
    decision = validate_live_order(
        config, side="BUY", symbol="BTCUSDT", current_equity=float("nan"),
        free_quote_balance=400, day_start_equity=400, last_price=100,
    )
    assert not decision.allowed
    assert "non-finite" in decision.reason


def test_order_guard_rejects_invalid_daily_loss_threshold():
    config = BotConfig(mode="live", live_enabled=True, api_key="k", api_secret="s",
                       live_confirmation=LIVE_CONFIRMATION)
    decision = validate_live_order(
        config, side="BUY", symbol="BTCUSDT", current_equity=400,
        free_quote_balance=400, day_start_equity=400, last_price=100,
        daily_loss_fraction=float("nan"),
    )
    assert not decision.allowed
    assert "threshold" in decision.reason


@pytest.mark.parametrize("bad_cash", [0.0, -1.0, float("nan"), float("inf")])
def test_config_rejects_invalid_paper_starting_cash(bad_cash):
    config = BotConfig(initial_cash=bad_cash)
    with pytest.raises(ValueError, match="PAPER_INITIAL_CASH"):
        config.validate()
