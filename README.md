# Binance Crypto Bot — safe starter

A research and paper-trading project. **This repository does not place live orders** and contains no Binance credentials.

## Current status
- Public Binance candle download (no API key needed)
- Long-only SMA crossover backtest with configurable fee and slippage assumptions
- No live order executor and no automated paper-trading loop yet
- No leverage or futures
- Risk limits are configuration examples, not guarantees against loss

## Start locally
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

## Run a historical backtest

This fetches recent public candles and simulates a simple moving-average strategy. It does not place orders or access your account.

```bash
PYTHONPATH=src python scripts/run_backtest.py --symbol BTCUSDT --interval 1h --limit 500 --cash 400
```

Optional parameters include `--fast 10 --slow 30 --fee 0.001 --slippage 0.0005`. The defaults assume 0.1% fee and 0.05% slippage per position change; actual costs depend on your account and execution. A recent-candle backtest is only a smoke test, not evidence of a robust strategy. We still need historical out-of-sample validation and better execution assumptions.

## Safety rules
1. Never commit API keys, secrets, recovery codes, or account data.
2. Do not enable withdrawal permissions on any API key.
3. Use public market data and simulated balances first.
4. Test strategies out-of-sample and include fees/slippage before considering live trading.
5. A stop-loss cannot guarantee the exit price; losses can exceed estimates.
6. Never treat backtest performance as a promise of future returns.

## Planned stages
1. Validate risk and strategy code.
2. Add public market-data ingestion. (implemented)
3. Add a first fee/slippage-aware research backtest. (implemented; needs stronger validation)
4. Validate with longer historical and out-of-sample datasets.
5. Add paper trading and monitor failure modes.
6. Only after review, consider a separate live-execution module with strict safeguards.

## Important
GitHub Actions is suitable for tests and scheduled research jobs, not for continuous low-latency trading. Live trading would require a separately secured always-on runtime and explicit configuration.
