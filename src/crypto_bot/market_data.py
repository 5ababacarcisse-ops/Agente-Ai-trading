"""Public Binance market-data loader. No API key or trading permission is required."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.binance.com/api/v3/klines"
ALLOWED_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h",
    "6h", "8h", "12h", "1d", "3d", "1w", "1M",
}


@dataclass(frozen=True)
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int

    @property
    def timestamp(self) -> str:
        return datetime.fromtimestamp(
            self.open_time / 1000, tz=timezone.utc
        ).isoformat()


def fetch_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 500,
    timeout: float = 15.0,
) -> list[Candle]:
    """Fetch up to 1000 recent candles from Binance's public REST endpoint."""
    symbol = symbol.strip().upper()
    if not symbol or not symbol.isalnum():
        raise ValueError("symbol must contain only letters and numbers")
    if interval not in ALLOWED_INTERVALS:
        raise ValueError(f"unsupported interval: {interval}")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")

    url = f"{BASE_URL}?{urlencode({'symbol': symbol, 'interval': interval, 'limit': limit})}"
    request = Request(url, headers={"User-Agent": "research-paper-bot/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Unable to fetch Binance public market data: {exc}") from exc

    if not isinstance(payload, list):
        # Binance returns a JSON object with a message when the request fails.
        message = payload.get("msg", "unexpected API response") if isinstance(payload, dict) else "unexpected API response"
        raise RuntimeError(f"Binance API error: {message}")

    candles = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 7:
            raise RuntimeError("Unexpected kline row returned by Binance")
        candles.append(Candle(
            open_time=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            close_time=int(row[6]),
        ))
    return candles
