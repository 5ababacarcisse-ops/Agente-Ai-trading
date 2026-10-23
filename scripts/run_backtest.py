"""Run a research backtest on recent public Binance candles.

Example:
  PYTHONPATH=src python scripts/run_backtest.py --symbol BTCUSDT --interval 1h
"""
import argparse

from crypto_bot.backtest import backtest_sma_crossover
from crypto_bot.market_data import fetch_klines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--cash", type=float, default=400.0)
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    parser.add_argument("--fee", type=float, default=0.001, help="fee fraction per position change; default 0.1%%")
    parser.add_argument("--slippage", type=float, default=0.0005, help="slippage fraction per position change; default 0.05%%")
    args = parser.parse_args()

    candles = fetch_klines(args.symbol, args.interval, args.limit)
    result = backtest_sma_crossover(
        candles,
        initial_cash=args.cash,
        fast_window=args.fast,
        slow_window=args.slow,
        fee_fraction=args.fee,
        slippage_fraction=args.slippage,
    )
    print(f"Symbol: {args.symbol.upper()} | interval: {args.interval}")
    print(f"Candles: {result.candles_used} | position changes: {result.trades}")
    print(f"Initial cash: {result.initial_cash:.2f} USDT")
    print(f"Final simulated equity: {result.final_equity:.2f} USDT")
    print(f"Total return: {result.total_return_fraction * 100:.2f}%")
    print(f"Maximum drawdown: {result.max_drawdown_fraction * 100:.2f}%")
    print("Research only: past results do not predict future returns.")


if __name__ == "__main__":
    main()
