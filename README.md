# Binance Crypto Bot — safe starter

A research and paper-trading project. **This repository does not place live orders** and contains no Binance credentials.

## Current status
- Backtesting / paper-trading foundation only
- No live order executor
- No leverage or futures
- Risk limits are configuration examples, not guarantees against loss

## Start locally
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

## Safety rules
1. Never commit API keys, secrets, recovery codes, or account data.
2. Do not enable withdrawal permissions on any API key.
3. Use public market data and simulated balances first.
4. Test strategies out-of-sample and include fees/slippage before considering live trading.
5. A stop-loss cannot guarantee the exit price; losses can exceed estimates.
6. Never treat backtest performance as a promise of future returns.

## Planned stages
1. Validate risk and strategy code.
2. Add public market-data ingestion.
3. Add backtests with realistic fees and slippage.
4. Run paper trading and monitor failure modes.
5. Only after review, consider a separate live-execution module with strict safeguards.

## Important
GitHub Actions is suitable for tests and scheduled research jobs, not for continuous low-latency trading. Live trading would require a separately secured always-on runtime and explicit configuration.
