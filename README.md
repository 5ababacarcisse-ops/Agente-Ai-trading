# Binance Crypto Bot

A Python research and trading project for Binance Spot. Paper mode is the default. Live mode exists but is **disabled unless several explicit safety gates are configured**. No credentials are stored in this repository.

## Current capabilities
- Fetch public Binance Spot candles without credentials.
- Run a simple long-only SMA crossover backtest with fee/slippage assumptions.
- Run a continuous local paper simulation with persistent local portfolio state.
- Optional live Spot order module, defaulting to Binance Spot Testnet when live mode is explicitly enabled; mainnet requires an additional explicit setting. It has a bot-owned position ledger, symbol filters, no leverage, and a daily loss guard.
- GitHub Actions runs automated tests; it is not a continuous trading host.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

## Historical backtest

```bash
PYTHONPATH=src python scripts/run_backtest.py --symbol BTCUSDT --interval 1h --limit 500 --cash 400
```

The default costs are assumptions (0.1% fee and 0.05% slippage per position change), not guaranteed actual costs. Recent candles are only a smoke test. For longer history, use `PYTHONPATH=src python scripts/run_backtest.py --symbol BTCUSDT --interval 1h --days 365 --cash 400`. Historical downloads are capped at 100,000 candles. A proper evaluation also needs out-of-sample testing, benchmarks, and realistic execution modelling.

## Continuous paper trading

```bash
cp .env.example .env
# Edit .env only for non-secret settings, then export its variables in your shell.
set -a
. ./.env
set +a
PYTHONPATH=src python scripts/run_bot.py
```

Paper state is written to `data/paper_state.json`; it is ignored by Git. It is a simple simulation and should not be interpreted as an estimate of future returns.

An optional Render background-worker Blueprint is included in `render.yaml`. It is configured for paper mode only and attaches persistent storage. Applying it may create billable infrastructure (Starter worker + disk); **nothing has been deployed automatically**. Review current Render pricing before creating resources.

## Live trading: intentionally gated

Live trading uses real money. Do not enable it until you have reviewed the source and run paper mode long enough to understand losses, drawdowns, fees, and failure modes. Backtests cannot guarantee future results.

If you later choose to enable live trading, configure these only in a secure runtime (never in a committed file):
- `TRADING_MODE=live`
- `LIVE_TRADING_ENABLED=true`
- `LIVE_TRADING_CONFIRMATION=I_UNDERSTAND_REAL_MONEY_RISK`
- `BINANCE_TESTNET=true` (default; use Testnet credentials for dry execution tests)
- `BINANCE_API_KEY` and `BINANCE_API_SECRET`

For real funds, `BINANCE_TESTNET=false` is an additional explicit switch. Do not set it until the testnet workflow and paper results have been reviewed.

Create a dedicated Binance API key with **Spot trading only**, withdrawals disabled, and IP restrictions where supported. Never send API keys to ChatGPT or put them in GitHub source files. Start with a small amount you can afford to lose.

The live runner is limited to USDT-quoted Spot pairs, long-only, no leverage/futures, one configured symbol, and a maximum allocation fraction capped at 10% (default 10%), restricted to BTCUSDT or ETHUSDT. It tracks only positions opened by this bot and refuses to automatically sell pre-existing holdings. It estimates equity from the traded base asset and quote balance; this is not a full account NAV calculation. State is stored locally in `data/live_state.json` (or `LIVE_STATE_PATH`), so run only one instance at a time and protect that machine and state file. API errors, partial fills, exchange rule changes, outages, or state loss can still cause losses or require manual intervention.

**Do not use GitHub Actions as the live trading host.** Use a secured, always-on runtime only after paper validation. The bot is software, not a guarantee of profit or capital preservation.
