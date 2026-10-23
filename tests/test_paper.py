import pytest

from crypto_bot.paper import PaperPortfolio


def test_paper_buy_and_sell_with_fees(tmp_path):
    portfolio = PaperPortfolio(str(tmp_path / "state.json"), initial_cash=400)
    portfolio.buy(price=100, quote_amount=100, fee_fraction=0.001, candle_id=1)
    assert portfolio.state.cash == pytest.approx(299.9)
    assert portfolio.state.base_quantity == pytest.approx(1.0)
    portfolio.sell(price=110, fee_fraction=0.001, candle_id=2)
    assert portfolio.state.base_quantity == 0
    assert portfolio.state.cash == pytest.approx(409.79)



def test_paper_state_rejects_nonfinite_balance(tmp_path):
    path = tmp_path / "state.json"
    path.write_text('{"cash": NaN}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="refusing to reset"):
        PaperPortfolio(str(path), initial_cash=400)
