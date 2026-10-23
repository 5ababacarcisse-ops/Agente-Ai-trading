"""Minimal Binance Spot REST client.

Public endpoints need no credentials. Signed account/order endpoints are only
reachable when explicitly enabled through validated live configuration.
Never grant withdrawal permission to the API key.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceAPIError(RuntimeError):
    pass


class BinanceSpotClient:
    def __init__(self, api_key: str = "", api_secret: str = "", timeout: float = 15.0):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

    def _request(self, method: str, path: str, params: dict | None = None, signed: bool = False):
        params = dict(params or {})
        headers = {"User-Agent": "crypto-research-bot/0.1"}
        if signed:
            if not self.api_key or not self.api_secret:
                raise BinanceAPIError("API credentials are not configured")
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            query = urlencode(params)
            signature = hmac.new(
                self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            query = f"{query}&signature={signature}"
            headers["X-MBX-APIKEY"] = self.api_key
        else:
            query = urlencode(params)
        url = "https://api.binance.com" + path
        if method.upper() == "GET" and query:
            url += "?" + query
            data = None
        else:
            data = query.encode("utf-8") if query else None
            if data is not None:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise BinanceAPIError(f"Binance HTTP {exc.code}: {body[:500]}") from exc
        except (URLError, TimeoutError) as exc:
            raise BinanceAPIError(f"Binance request failed: {exc}") from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise BinanceAPIError("Binance returned invalid JSON") from exc

    def account(self):
        return self._request("GET", "/api/v3/account", signed=True)

    def exchange_info(self, symbol: str):
        return self._request("GET", "/api/v3/exchangeInfo", {"symbol": symbol})

    def market_buy_quote(self, symbol: str, quote_order_qty: str):
        """Submit a market BUY. Caller must enforce live gates and sizing."""
        if float(quote_order_qty) <= 0:
            raise ValueError("quote_order_qty must be positive")
        return self._request("POST", "/api/v3/order", {
            "symbol": symbol, "side": "BUY", "type": "MARKET",
            "quoteOrderQty": quote_order_qty, "newOrderRespType": "FULL",
        }, signed=True)

    def market_sell_quantity(self, symbol: str, quantity: str):
        """Submit a market SELL. Caller must enforce live gates and sizing."""
        if float(quantity) <= 0:
            raise ValueError("quantity must be positive")
        return self._request("POST", "/api/v3/order", {
            "symbol": symbol, "side": "SELL", "type": "MARKET",
            "quantity": quantity, "newOrderRespType": "FULL",
        }, signed=True)
