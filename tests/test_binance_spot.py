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
