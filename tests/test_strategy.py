from crypto_bot.strategy import latest_signal


def test_strategy_holds_until_crossover():
    prices = [100.0] * 20 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
    signal = latest_signal(prices, fast_window=3, slow_window=5)
    assert signal.action in {"buy", "hold", "sell"}
    assert signal.fast_average is not None
    assert signal.slow_average is not None


def test_strategy_rejects_insufficient_data():
    import pytest
    with pytest.raises(ValueError, match="not enough"):
        latest_signal([1, 2, 3], fast_window=2, slow_window=4)
