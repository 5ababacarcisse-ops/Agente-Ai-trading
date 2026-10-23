import pytest

from crypto_bot.binance_spot import BinanceAPIError, BinanceSpotClient


def test_client_rejects_untrusted_base_url():
    with pytest.raises(ValueError, match="official Binance"):
        BinanceSpotClient(base_url="https://attacker.example")


def test_signed_endpoint_requires_credentials_before_network():
    client = BinanceSpotClient()
    with pytest.raises(BinanceAPIError, match="credentials"):
        client.account()


def test_client_accepts_official_testnet_base_url():
    client = BinanceSpotClient(base_url="https://testnet.binance.vision")
    assert client.base_url == "https://testnet.binance.vision"



def test_open_orders_uses_signed_endpoint(monkeypatch):
    client = BinanceSpotClient("key", "secret")
    captured = {}

    def fake_request(method, path, params=None, signed=False):
        captured.update(method=method, path=path, params=params, signed=signed)
        return []

    monkeypatch.setattr(client, "_request", fake_request)
    assert client.open_orders("BTCUSDT") == []
    assert captured["method"] == "GET"
    assert captured["path"] == "/api/v3/openOrders"
    assert captured["params"] == {"symbol": "BTCUSDT"}
    assert captured["signed"] is True
