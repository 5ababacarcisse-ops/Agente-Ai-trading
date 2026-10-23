import pytest

from crypto_bot.market_data import fetch_historical_klines, fetch_klines


def test_recent_fetch_rejects_invalid_interval():
    with pytest.raises(ValueError, match="unsupported interval"):
        fetch_klines(interval="2weeks")


def test_recent_fetch_rejects_excessive_limit():
    with pytest.raises(ValueError, match="between 1 and 1000"):
        fetch_klines(limit=1001)


def test_historical_fetch_rejects_reversed_time_range():
    with pytest.raises(ValueError, match="greater than"):
        fetch_historical_klines(start_time_ms=2000, end_time_ms=1000)


def test_historical_fetch_caps_maximum_candles():
    with pytest.raises(ValueError, match="max_candles"):
        fetch_historical_klines(start_time_ms=0, end_time_ms=1, max_candles=100001)



def test_historical_fetch_rejects_silent_truncation(monkeypatch):
    import json
    from crypto_bot import market_data

    payload = [
        [100, "1", "2", "0.5", "1.5", "10", 150],
        [200, "1.5", "2", "1", "1.8", "12", 250],
    ]

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(market_data, "urlopen", lambda *args, **kwargs: FakeResponse())
    with pytest.raises(RuntimeError, match="exceeds the 2-candle safety cap"):
        fetch_historical_klines(
            start_time_ms=0, end_time_ms=1000, max_candles=2
        )
