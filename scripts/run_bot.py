"""Run the bot in paper mode by default.

Live mode requires multiple explicit environment flags and still trades only
Spot, long-only, one symbol, and at most the configured small allocation.
Do not run live mode until you've reviewed all source code and tested paper mode.
"""
from __future__ import annotations

import logging
from math import isfinite
import os
import signal
import time
from decimal import Decimal, ROUND_DOWN

from crypto_bot.binance_spot import BinanceSpotClient
from crypto_bot.config import BotConfig
from crypto_bot.live_guard import validate_live_order
from crypto_bot.market_data import fetch_klines
from crypto_bot.live_state import LiveStateStore
from crypto_bot.paper import PaperPortfolio
from crypto_bot.strategy import latest_signal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("crypto_bot")
STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


def _split_symbol(symbol: str) -> tuple[str, str]:
    # Intentionally restrict the initial live release to USDT-quoted markets.
    if not symbol.endswith("USDT") or len(symbol) <= 4:
        raise ValueError("This initial live runner supports only USDT-quoted Spot pairs")
    return symbol[:-4], "USDT"


def _format_quantity(quantity: float, step_size: str) -> str:
    step = Decimal(step_size)
    value = Decimal(str(quantity))
    rounded = (value / step).to_integral_value(rounding=ROUND_DOWN) * step
    return format(rounded, "f")


def _format_quote_amount(amount: float) -> str:
    # USDT quoteOrderQty is rounded down to cents to avoid exceeding free balance.
    return format(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_DOWN), "f")


def run_paper(config: BotConfig) -> None:
    portfolio = PaperPortfolio(path=os.getenv("PAPER_STATE_PATH", "data/paper_state.json"), initial_cash=float(os.getenv("PAPER_INITIAL_CASH", "400")))
    LOG.warning("PAPER MODE: simulated balance only; no live orders can be sent.")
    while not STOP:
        candles = fetch_klines(config.symbol, config.interval, config.candles)
        # Ignore the last candle because it may still be forming.
        closed = candles[:-1]
        signal = latest_signal([c.close for c in closed], config.fast_window, config.slow_window)
        last = closed[-1]
        price = last.close
        portfolio.roll_day(price)
        state = portfolio.state
        equity = portfolio.equity(price)
        loss = max(0.0, (state.day_start_equity - equity) / state.day_start_equity) if state.day_start_equity else 1.0
        if loss >= config.max_daily_loss_fraction and not state.halted:
            state.halted = True
            portfolio.save()
            LOG.error("Daily paper loss threshold reached; new entries halted for the UTC day.")
        if last.open_time > state.last_signal_candle:
            if signal.action == "sell" and state.base_quantity > 0:
                # Risk halts block new entries, never exits from an existing position.
                portfolio.sell(price * (1 - config.slippage_fraction), config.fee_fraction, last.open_time)
                LOG.info("PAPER SELL signal | %s | close=%.4f | equity=%.2f", config.symbol, price, portfolio.equity(price))
            elif not state.halted and signal.action == "buy" and state.base_quantity == 0:
                allocation = min(equity * config.max_allocation_fraction, state.cash)
                portfolio.buy(price * (1 + config.slippage_fraction), allocation, config.fee_fraction, last.open_time)
                LOG.info("PAPER BUY signal | %s | close=%.4f | equity=%.2f", config.symbol, price, portfolio.equity(price))
            else:
                state.last_signal_candle = last.open_time
                portfolio.save()
        LOG.info("mode=paper symbol=%s signal=%s reason=%s price=%.4f equity=%.2f cash=%.2f base=%.8f",
                 config.symbol, signal.action, signal.reason, price, portfolio.equity(price),
                 portfolio.state.cash, portfolio.state.base_quantity)
        for _ in range(config.poll_seconds):
            if STOP:
                break
            time.sleep(1)


def run_live(config: BotConfig) -> None:
    # Config validation must already have enforced all explicit live gates.
    base_url = "https://testnet.binance.vision" if config.testnet else "https://api.binance.com"
    client = BinanceSpotClient(config.api_key, config.api_secret, base_url=base_url)
    base_asset, quote_asset = _split_symbol(config.symbol)
    state_store = LiveStateStore(os.getenv("LIVE_STATE_PATH", "data/live_state.json"))
    if state_store.state.pending_order:
        raise RuntimeError(
            f"Unresolved order intent ({state_store.state.pending_order}); inspect Binance order/trade history, "
            "reconcile balances, and clear it manually only after verification. Refusing to trade."
        )
    info = client.exchange_info(config.symbol)
    symbols = info.get("symbols", [])
    if not symbols or symbols[0].get("status") != "TRADING" or symbols[0].get("isSpotTradingAllowed") is False:
        raise RuntimeError("Symbol is not currently available for Spot trading")
    filters = {f.get("filterType"): f for f in symbols[0].get("filters", [])}
    lot = filters.get("LOT_SIZE", {})
    step_size = lot.get("stepSize")
    min_qty = float(lot.get("minQty", "0"))
    min_notional_filter = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
    min_notional = float(min_notional_filter.get("minNotional", "0"))
    if not step_size:
        raise RuntimeError("Could not read LOT_SIZE step size; refusing to trade")
    LOG.critical("LIVE EXECUTION enabled on %s. Spot only; no leverage, no withdrawals; allocation cap %.1f%%.",
                 "TESTNET" if config.testnet else "MAINNET", config.max_allocation_fraction * 100)
    LOG.critical("Real funds are at risk. Stop with Ctrl+C.")
    while not STOP:
        candles = fetch_klines(config.symbol, config.interval, config.candles, base_url=base_url)
        # Never trade on the currently forming candle.
        closed = candles[:-1]
        last = closed[-1]
        signal = latest_signal([c.close for c in closed], config.fast_window, config.slow_window)
        state = state_store.state
        is_new_candle = last.open_time > state.last_signal_candle

        # Refresh account equity every poll so the daily loss guard can trip
        # during a forming candle; order decisions remain candle-gated.
        account = client.account()
        balances = {r["asset"]: float(r.get("free", 0)) + float(r.get("locked", 0))
                    for r in account.get("balances", [])}
        free_balances = {r["asset"]: float(r.get("free", 0)) for r in account.get("balances", [])}
        free_quote = free_balances.get(quote_asset, 0.0)
        free_base = free_balances.get(base_asset, 0.0)
        # Approximate account equity from the traded base asset and quote balance.
        # Other assets are deliberately excluded, so this is not total account NAV.
        equity = balances.get(quote_asset, 0.0) + balances.get(base_asset, 0.0) * last.close
        state_store.roll_day(equity)
        state = state_store.state
        day_loss = max(0.0, (state.day_start_equity - equity) / state.day_start_equity) if state.day_start_equity > 0 else 0.0
        if day_loss >= config.max_daily_loss_fraction:
            state.halted = True
            state_store.save()
            LOG.error("Daily loss threshold reached (%.2f%%); new entries halted for UTC day.", day_loss * 100)
        if is_new_candle and signal.action in {"buy", "sell"}:
            open_orders = client.open_orders(config.symbol)
            if not isinstance(open_orders, list):
                raise RuntimeError("Unexpected open-orders response; refusing to trade")
            if open_orders:
                raise RuntimeError("Open Spot orders exist for this symbol; reconcile them before restarting")
        if state.halted and not (is_new_candle and signal.action == "sell" and state.owned_quantity > 0):
            LOG.warning("New entries halted for today; existing-position exits remain permitted. signal=%s equity_estimate=%.2f", signal.action, equity)
            if is_new_candle:
                state.last_signal_candle = last.open_time
                state_store.save()
        elif is_new_candle and signal.action == "buy" and state.owned_quantity <= 0:
            decision = validate_live_order(
                config, side="BUY", symbol=config.symbol, current_equity=equity,
                free_quote_balance=free_quote, day_start_equity=state.day_start_equity,
                last_price=last.close,
            )
            if decision.allowed:
                amount = min(decision.quote_amount, free_quote)
                if amount < min_notional:
                    LOG.info("BUY skipped: order value %.2f is below exchange minimum %.2f", amount, min_notional)
                    state.last_signal_candle = last.open_time
                    state_store.save()
                elif balances.get(base_asset, 0.0) > 0:
                    LOG.warning("BUY skipped: account already has %s outside this bot's ownership ledger", base_asset)
                    state.last_signal_candle = last.open_time
                    state_store.save()
                else:
                    # Persist intent before sending. If the network fails after Binance accepts
                    # the order, the next process start will halt for manual reconciliation.
                    state.pending_order = f"BUY {config.symbol} candle={last.open_time}"
                    state_store.save()
                    response = client.market_buy_quote(config.symbol, _format_quote_amount(amount))
                    executed = float(response.get("executedQty", 0))
                    if response.get("status") not in {"FILLED", "PARTIALLY_FILLED"} or not isfinite(executed) or executed <= 0:
                        raise RuntimeError("Buy order was not confirmed; pending intent retained. Inspect Binance order history.")
                    state.owned_quantity = executed
                    state.last_signal_candle = last.open_time
                    state.pending_order = ""
                    state_store.save()
                    LOG.warning("LIVE BUY filled/partial | orderId=%s qty=%s status=%s",
                                response.get("orderId"), executed, response.get("status"))
            else:
                LOG.warning("BUY blocked: %s", decision.reason)
                state.last_signal_candle = last.open_time
                state_store.save()
        elif is_new_candle and signal.action == "sell" and state.owned_quantity > 0:
            quantity = min(state.owned_quantity, free_base)
            quantity_text = _format_quantity(quantity, step_size)
            rounded_quantity = float(quantity_text)
            if rounded_quantity < min_qty or rounded_quantity * last.close < min_notional:
                LOG.warning("SELL skipped: bot-owned quantity below exchange minimum; manual review needed")
                state.last_signal_candle = last.open_time
                state_store.save()
            else:
                state.pending_order = f"SELL {config.symbol} candle={last.open_time}"
                state_store.save()
                response = client.market_sell_quantity(config.symbol, quantity_text)
                executed = float(response.get("executedQty", 0))
                if response.get("status") not in {"FILLED", "PARTIALLY_FILLED"} or not isfinite(executed) or executed <= 0:
                    raise RuntimeError("Sell order was not confirmed; pending intent retained. Inspect Binance order history.")
                state.owned_quantity = max(0.0, state.owned_quantity - executed)
                state.last_signal_candle = last.open_time
                state.pending_order = ""
                state_store.save()
                LOG.warning("LIVE SELL filled/partial | orderId=%s qty=%s remaining_owned=%.8f status=%s",
                            response.get("orderId"), executed, state.owned_quantity, response.get("status"))
        elif is_new_candle:
            LOG.info("LIVE no order | signal=%s reason=%s equity_estimate=%.2f owned_qty=%.8f",
                     signal.action, signal.reason, equity, state.owned_quantity)
            state.last_signal_candle = last.open_time
            state_store.save()
        else:
            LOG.info("LIVE monitoring | signal=%s equity_estimate=%.2f day_loss=%.2f%% halted=%s",
                     signal.action, equity, day_loss * 100, state.halted)
        for _ in range(config.poll_seconds):
            if STOP:
                break
            time.sleep(1)

def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    config = BotConfig.from_env()
    config.validate()
    if config.mode == "live":
        run_live(config)
    else:
        run_paper(config)


if __name__ == "__main__":
    main()
