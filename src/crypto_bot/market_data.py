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
    base_url: str = "https://api.binance.com",
) -> list[Candle]:
    """Fetch up to 1000 recent candles from Binance's public REST endpoint."""
    symbol = symbol.strip().upper()
    if not symbol or not symbol.isalnum():
        raise ValueError("symbol must contain only letters and numbers")
    if interval not in ALLOWED_INTERVALS:
        raise ValueError(f"unsupported interval: {interval}")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")

    endpoint = base_url.rstrip("/") + "/api/v3/klines"
    url = f"{endpoint}?{urlencode({'symbol': symbol, 'interval': interval, 'limit': limit})}"
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



def fetch_historical_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    timeout: float = 15.0,
    base_url: str = "https://api.binance.com",
    max_candles: int = 100_000,
) -> list[Candle]:
    """Paginate public candle history for a backtest.

    Times are Unix milliseconds. The function caps downloads to avoid accidental
    huge requests and stops safely if the API returns no progress.
    """
    import time

    symbol = symbol.strip().upper()
    if not symbol or not symbol.isalnum():
        raise ValueError("symbol must contain only letters and numbers")
    if interval not in ALLOWED_INTERVALS:
        raise ValueError(f"unsupported interval: {interval}")
    if max_candles < 1 or max_candles > 100_000:
        raise ValueError("max_candles must be between 1 and 100000")
    start = 0 if start_time_ms is None else int(start_time_ms)
    end = int(time.time() * 1000) if end_time_ms is None else int(end_time_ms)
    if start < 0 or end <= start:
        raise ValueError("end_time_ms must be greater than a non-negative start_time_ms")

    endpoint = base_url.rstrip("/") + "/api/v3/klines"
    all_candles: list[Candle] = []
    cursor = start
    while cursor < end and len(all_candles) < max_candles:
        params = {"symbol": symbol, "interval": interval, "startTime": cursor,
                  "endTime": end, "limit": min(1000, max_candles - len(all_candles))}
        request = Request(
            f"{endpoint}?{urlencode(params)}",
            headers={"User-Agent": "research-paper-bot/0.1"},
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Unable to fetch Binance historical data: {exc}") from exc
        if not isinstance(payload, list):
            message = payload.get("msg", "unexpected API response") if isinstance(payload, dict) else "unexpected API response"
            raise RuntimeError(f"Binance API error: {message}")
        if not payload:
            break
        page: list[Candle] = []
        for row in payload:
            if not isinstance(row, list) or len(row) < 7:
                raise RuntimeError("Unexpected kline row returned by Binance")
            page.append(Candle(
                open_time=int(row[0]), high=float(row[2]), low=float(row[3]),
                open=float(row[1]), close=float(row[4]), volume=float(row[5]),
                close_time=int(row[6]),
            ))
        # Avoid duplicates if the upstream endpoint repeats the boundary candle.
        known = {c.open_time for c in all_candles}
        page = [c for c in page if c.open_time not in known and c.open_time < end]
        if not page:
            break
        all_candles.extend(page)
        next_cursor = max(c.open_time for c in page) + 1
        if next_cursor <= cursor:
            raise RuntimeError("Historical pagination made no progress; refusing to loop")
        cursor = next_cursor

    all_candles.sort(key=lambda candle: candle.open_time)
    return all_candles
