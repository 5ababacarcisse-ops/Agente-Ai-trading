"""Evaluate a strategy chronologically on train and out-of-sample test periods.

Example:
  PYTHONPATH=src python scripts/evaluate_strategy.py --symbol BTCUSDT --interval 1h --days 365
"""
import argparse
from datetime import datetime, timedelta, timezone

from crypto_bot.backtest import backtest_sma_crossover
from crypto_bot.market_data import fetch_historical_klines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--cash", type=float, default=400.0)
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--fee", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    args = parser.parse_args()

    if not 30 <= args.days <= 3650:
        parser.error("--days must be between 30 and 3650")
    if not 0.5 <= args.train_fraction <= 0.9:
        parser.error("--train-fraction must be between 0.5 and 0.9")
    if args.fast < 1 or args.slow <= args.fast:
        parser.error("require 1 <= --fast < --slow")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    candles = fetch_historical_klines(
        args.symbol,
        args.interval,
        start_time_ms=int(start.timestamp() * 1000),
        end_time_ms=int(end.timestamp() * 1000),
    )
    # Historical endpoints can include the still-forming candle.
    candles = candles[:-1]
    split = int(len(candles) * args.train_fraction)
    if split < args.slow + 2 or len(candles) - split < args.slow + 2:
        parser.error("not enough candles for both train and test periods; use more days or a shorter interval")

    common = dict(
        initial_cash=args.cash,
        fast_window=args.fast,
        slow_window=args.slow,
        fee_fraction=args.fee,
        slippage_fraction=args.slippage,
    )
    train = backtest_sma_crossover(candles[:split], **common)
    # Reuse historical warm-up candles, but score returns only from the split
    # onward. At the split, the simulated portfolio starts in cash.
    test = backtest_sma_crossover(candles, start_index=split, **common)

    print(f"Symbol: {args.symbol.upper()} | interval: {args.interval}")
    print(f"Total completed candles: {len(candles)} | split index: {split}")
    print(f"Train bars: {split} | test bars scored: {len(candles) - split}")
    for label, result in (("TRAIN", train), ("OUT-OF-SAMPLE TEST", test)):
        print(f"\n{label}")
        print(f"  Position changes: {result.trades}")
        print(f"  Final simulated equity: {result.final_equity:.2f} USDT")
        print(f"  Strategy return: {result.total_return_fraction * 100:.2f}%")
        print(f"  Buy-and-hold return: {result.buy_hold_return_fraction * 100:.2f}%")
        print(f"  Maximum drawdown: {result.max_drawdown_fraction * 100:.2f}%")
    print("\nResearch only: the split reduces in-sample bias but does not prove future profitability.")


if __name__ == "__main__":
    main()
