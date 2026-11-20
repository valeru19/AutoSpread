"""Табличные и property-тесты MarginService."""

from decimal import Decimal, InvalidOperation
from typing import Any

import pytest
from dishka import make_async_container
from hypothesis import given, settings, strategies as st

from app.api.dto.margin import (
    AdInput,
    InstrumentInput,
    MarginConfig,
    MarginRequest,
)
from app.api.services.margin_service import (
    REJECT_BELOW_MARGIN,
    REJECT_BELOW_MIN_LIMIT,
    REJECT_BLACKLISTED,
    REJECT_COUNTERPARTY_BELOW,
    REJECT_CURRENCY_MISMATCH,
    REJECT_EMPTY_INTERSECTION,
    REJECT_NO_INSTRUMENT,
    REJECT_SAME_AD,
    MarginService,
    MarginServiceProvider,
    round_crypto,
    round_pct,
)
from app.core.service_exceptions import MarginInputError


def _ad(
    *,
    ad_snapshot_id: int = 1,
    counterparty_id: int = 10,
    currency: str = "RUB",
    side: str = "sell",
    price: str = "90",
    available_amount: str = "1000",
    min_amount: str = "0",
    max_amount: str = "1000000",
    payment_methods: list[str] | None = None,
    is_blacklisted: bool = False,
    rating: str | None = "98",
    orders_count: int | None = 100,
) -> AdInput:
    return AdInput(
        ad_snapshot_id=ad_snapshot_id,
        counterparty_id=counterparty_id,
        currency=currency,
        side=side,
        price=Decimal(price),
        available_amount=Decimal(available_amount),
        min_amount=Decimal(min_amount),
        max_amount=Decimal(max_amount),
        payment_methods=payment_methods or ["SBP"],
        is_blacklisted=is_blacklisted,
        rating=None if rating is None else Decimal(rating),
        orders_count=orders_count,
    )


def _cfg(
    *,
    min_net_margin_pct: str = "0",
    max_deal_usdt: str = "10000",
    buy_fee_pct: str = "0",
    sell_fee_pct: str = "0",
    fiat_cost_pct: str = "0",
    fees_verified: bool = True,
    min_counterparty_rating: str | None = None,
    min_counterparty_orders: int | None = None,
) -> MarginConfig:
    return MarginConfig(
        min_net_margin_pct=Decimal(min_net_margin_pct),
        max_deal_usdt=Decimal(max_deal_usdt),
        buy_fee_pct=Decimal(buy_fee_pct),
        sell_fee_pct=Decimal(sell_fee_pct),
        fiat_cost_pct=Decimal(fiat_cost_pct),
        fees_verified=fees_verified,
        min_counterparty_rating=(
            None
            if min_counterparty_rating is None
            else Decimal(min_counterparty_rating)
        ),
        min_counterparty_orders=min_counterparty_orders,
    )


def _instruments(
    *,
    currency: str = "RUB",
    method_code: str = "SBP",
    buy_id: int = 1,
    sell_id: int = 2,
) -> list[InstrumentInput]:
    return [
        InstrumentInput(
            instrument_id=buy_id,
            currency=currency,
            method_code=method_code,
            is_active=True,
        ),
        InstrumentInput(
            instrument_id=sell_id,
            currency=currency,
            method_code=method_code,
            is_active=True,
        ),
    ]


def _request(
    *,
    buy: AdInput | None = None,
    sell: AdInput | None = None,
    instruments: list[InstrumentInput] | None = None,
    config: MarginConfig | None = None,
    amount_cap: Decimal | None = None,
) -> MarginRequest:
    buy_ad = buy or _ad(ad_snapshot_id=1, side="sell", price="90")
    sell_ad = sell or _ad(
        ad_snapshot_id=2,
        counterparty_id=20,
        side="buy",
        price="92",
    )
    return MarginRequest(
        buy_ad=buy_ad,
        sell_ad=sell_ad,
        instruments=(
            _instruments() if instruments is None else instruments
        ),
        config=config or _cfg(),
        amount_cap=amount_cap,
    )


@pytest.fixture
def service() -> MarginService:
    return MarginService()


# --- А–Г: точные числа ---


def test_a_zero_fees(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", price="90", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="100"),
    )
    result = service.evaluate(req)
    assert result.accepted is True
    assert result.reject_reason is None
    assert result.buy_cost == Decimal("9000.0000")
    assert result.sell_revenue == Decimal("9200.0000")
    assert result.net_profit_fiat == Decimal("200.0000")
    assert result.net_margin_pct == Decimal("2.222222")
    assert result.gross_margin_pct == Decimal("2.222222")


def test_b_with_fees(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", price="90", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(
            max_deal_usdt="100",
            buy_fee_pct="0.1",
            sell_fee_pct="0.1",
            fiat_cost_pct="0.2",
        ),
    )
    result = service.evaluate(req)
    assert result.accepted is True
    assert result.buy_cost == Decimal("9027.0000")
    assert result.sell_revenue == Decimal("9190.8000")
    assert result.net_profit_fiat == Decimal("163.8000")
    assert result.net_margin_pct == Decimal("1.814556")
    assert result.gross_margin_pct == Decimal("2.222222")


def test_c_negative_margin_filled(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", price="92", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="90",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="100", min_net_margin_pct="0"),
    )
    result = service.evaluate(req)
    assert result.accepted is False
    assert result.reject_reason == REJECT_BELOW_MARGIN
    assert result.net_profit_fiat == Decimal("-200.0000")
    assert result.net_margin_pct == Decimal("-2.173913")
    assert result.gross_margin_pct == Decimal("-2.173913")
    assert result.buy_cost == Decimal("9200.0000")
    assert result.sell_revenue == Decimal("9000.0000")


def test_d_fractional_amount(service: MarginService) -> None:
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price="90.5",
            available_amount="333.333333",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="91.2",
            available_amount="333.333333",
        ),
        config=_cfg(max_deal_usdt="333.333333"),
    )
    result = service.evaluate(req)
    assert result.accepted is True
    assert result.net_margin_pct == Decimal("0.773481")
    assert result.gross_margin_pct == Decimal("0.773481")


# --- Д: порог ровно / чуть выше ---


def test_e_margin_exactly_on_threshold(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", price="90", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="100", min_net_margin_pct="2.222222"),
    )
    result = service.evaluate(req)
    assert result.accepted is True
    assert result.net_margin_pct == Decimal("2.222222")


def test_e_margin_threshold_one_ulp_higher(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", price="90", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="100", min_net_margin_pct="2.222223"),
    )
    result = service.evaluate(req)
    assert result.accepted is False
    assert result.reject_reason == REJECT_BELOW_MARGIN
    assert result.net_margin_pct == Decimal("2.222222")


# --- Е: причины отказа ---


def test_reject_currency_mismatch(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", currency="RUB"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            currency="USD",
            price="92",
        ),
    )
    result = service.evaluate(req)
    assert result.accepted is False
    assert result.reject_reason == REJECT_CURRENCY_MISMATCH
    assert result.buy_cost is None


def test_reject_same_ad(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=5, side="sell"),
        sell=_ad(ad_snapshot_id=5, counterparty_id=20, side="buy", price="92"),
    )
    result = service.evaluate(req)
    assert result.reject_reason == REJECT_SAME_AD


def test_reject_blacklisted_buy(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", is_blacklisted=True),
        sell=_ad(ad_snapshot_id=2, counterparty_id=20, side="buy", price="92"),
    )
    assert service.evaluate(req).reject_reason == REJECT_BLACKLISTED


def test_reject_blacklisted_sell(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            is_blacklisted=True,
        ),
    )
    assert service.evaluate(req).reject_reason == REJECT_BLACKLISTED


def test_reject_counterparty_rating(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", rating="50"),
        sell=_ad(ad_snapshot_id=2, counterparty_id=20, side="buy", price="92"),
        config=_cfg(min_counterparty_rating="90"),
    )
    assert service.evaluate(req).reject_reason == REJECT_COUNTERPARTY_BELOW


def test_reject_counterparty_orders(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", orders_count=5),
        sell=_ad(ad_snapshot_id=2, counterparty_id=20, side="buy", price="92"),
        config=_cfg(min_counterparty_orders=10),
    )
    assert service.evaluate(req).reject_reason == REJECT_COUNTERPARTY_BELOW


def test_counterparty_threshold_not_applied_when_unset(
    service: MarginService,
) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", rating="1", orders_count=1),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            rating="1",
            orders_count=1,
        ),
        config=_cfg(
            max_deal_usdt="100",
            min_counterparty_rating=None,
            min_counterparty_orders=None,
        ),
    )
    result = service.evaluate(req)
    assert result.accepted is True


def test_no_instrument_missing(service: MarginService) -> None:
    req = _request(instruments=[])
    assert service.evaluate(req).reject_reason == REJECT_NO_INSTRUMENT


def test_no_instrument_inactive(service: MarginService) -> None:
    inst = [
        InstrumentInput(
            instrument_id=1, currency="RUB", method_code="SBP", is_active=False
        )
    ]
    req = _request(instruments=inst)
    assert service.evaluate(req).reject_reason == REJECT_NO_INSTRUMENT


def test_no_instrument_wrong_currency(service: MarginService) -> None:
    inst = [
        InstrumentInput(
            instrument_id=1, currency="USD", method_code="SBP", is_active=True
        )
    ]
    req = _request(instruments=inst)
    assert service.evaluate(req).reject_reason == REJECT_NO_INSTRUMENT


def test_no_instrument_method_mismatch_case_sensitive(
    service: MarginService,
) -> None:
    buy = _ad(ad_snapshot_id=1, side="sell", payment_methods=["SBP"])
    sell = _ad(
        ad_snapshot_id=2, counterparty_id=20, side="buy", price="92",
        payment_methods=["SBP"],
    )
    inst = [
        InstrumentInput(
            instrument_id=1, currency="RUB", method_code="sbp", is_active=True
        )
    ]
    req = _request(buy=buy, sell=sell, instruments=inst)
    assert service.evaluate(req).reject_reason == REJECT_NO_INSTRUMENT


def test_instrument_picks_smallest_id(service: MarginService) -> None:
    inst = [
        InstrumentInput(
            instrument_id=5, currency="RUB", method_code="SBP", is_active=True
        ),
        InstrumentInput(
            instrument_id=2, currency="RUB", method_code="SBP", is_active=True
        ),
        InstrumentInput(
            instrument_id=9, currency="RUB", method_code="SBP", is_active=True
        ),
    ]
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        instruments=inst,
        config=_cfg(max_deal_usdt="100"),
    )
    result = service.evaluate(req)
    assert result.accepted is True
    assert result.buy_instrument_id == 2
    assert result.sell_instrument_id == 2


def test_empty_intersection_available_zero(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", available_amount="0"),
        sell=_ad(
            ad_snapshot_id=2, counterparty_id=20, side="buy", price="92"
        ),
    )
    result = service.evaluate(req)
    assert result.reject_reason == REJECT_EMPTY_INTERSECTION
    assert result.buy_cost is None


def test_empty_intersection_max_amount_too_small(
    service: MarginService,
) -> None:
    # max_amount / price < 1 crypto unit effectively → rounds down to 0
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price="90",
            max_amount="0.000000000000000001",
            available_amount="1000",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="1000",
        ),
        config=_cfg(max_deal_usdt="1000"),
    )
    # buy.max/price = 0.000000000000000001/90 → tiny, ROUND_DOWN → 0
    result = service.evaluate(req)
    assert result.reject_reason == REJECT_EMPTY_INTERSECTION


def test_below_min_limit_buy_leg(service: MarginService) -> None:
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price="90",
            available_amount="10",
            min_amount="10000",
            max_amount="1000000",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="10",
            min_amount="0",
        ),
        config=_cfg(max_deal_usdt="10"),
    )
    result = service.evaluate(req)
    assert result.reject_reason == REJECT_BELOW_MIN_LIMIT
    assert result.net_margin_pct is None


def test_below_min_limit_sell_leg(service: MarginService) -> None:
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price="90",
            available_amount="10",
            min_amount="0",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="10",
            min_amount="10000",
        ),
        config=_cfg(max_deal_usdt="10"),
    )
    assert service.evaluate(req).reject_reason == REJECT_BELOW_MIN_LIMIT


# --- Ж: пять слагаемых минимума + amount_cap ---


def test_amount_limited_by_buy_available(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", available_amount="7"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="100"),
    )
    assert service.evaluate(req).amount_token == Decimal("7")


def test_amount_limited_by_sell_available(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="8",
        ),
        config=_cfg(max_deal_usdt="100"),
    )
    assert service.evaluate(req).amount_token == Decimal("8")


def test_amount_limited_by_max_deal_usdt(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="9"),
    )
    assert service.evaluate(req).amount_token == Decimal("9")


def test_amount_limited_by_buy_max_over_price(service: MarginService) -> None:
    # max_amount/price = 450/90 = 5
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price="90",
            available_amount="100",
            max_amount="450",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
            max_amount="1000000",
        ),
        config=_cfg(max_deal_usdt="100"),
    )
    assert service.evaluate(req).amount_token == Decimal("5")


def test_amount_limited_by_sell_max_over_price(service: MarginService) -> None:
    # max_amount/price = 460/92 = 5
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price="90",
            available_amount="100",
            max_amount="1000000",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
            max_amount="460",
        ),
        config=_cfg(max_deal_usdt="100"),
    )
    assert service.evaluate(req).amount_token == Decimal("5")


def test_amount_cap_overrides_max_deal_usdt(service: MarginService) -> None:
    req = _request(
        buy=_ad(ad_snapshot_id=1, side="sell", available_amount="100"),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price="92",
            available_amount="100",
        ),
        config=_cfg(max_deal_usdt="50"),
        amount_cap=Decimal("11"),
    )
    assert service.evaluate(req).amount_token == Decimal("11")


# --- З: MarginInputError + build_config ---


def test_input_error_price_zero(service: MarginService) -> None:
    req = _request(buy=_ad(ad_snapshot_id=1, side="sell", price="0"))
    with pytest.raises(MarginInputError):
        service.evaluate(req)


def test_input_error_price_negative(service: MarginService) -> None:
    req = _request(buy=_ad(ad_snapshot_id=1, side="sell", price="-1"))
    with pytest.raises(MarginInputError):
        service.evaluate(req)


def test_input_error_negative_limits(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(buy=_ad(ad_snapshot_id=1, side="sell", min_amount="-1"))
        )
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(buy=_ad(ad_snapshot_id=1, side="sell", max_amount="-1"))
        )
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(
                buy=_ad(ad_snapshot_id=1, side="sell", available_amount="-1")
            )
        )


def test_input_error_amount_cap_zero(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.evaluate(_request(amount_cap=Decimal("0")))


def test_input_error_wrong_sides(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(
                buy=_ad(ad_snapshot_id=1, side="buy"),
                sell=_ad(
                    ad_snapshot_id=2, counterparty_id=20, side="sell", price="92"
                ),
            )
        )


def test_input_error_nan_price(service: MarginService) -> None:
    buy = AdInput.model_construct(
        **{**_ad(ad_snapshot_id=1, side="sell").model_dump(), "price": Decimal("NaN")}
    )
    with pytest.raises(MarginInputError):
        service.evaluate(_request(buy=buy))


def test_input_error_infinity_amount_cap(service: MarginService) -> None:
    base = _request()
    req = MarginRequest.model_construct(
        buy_ad=base.buy_ad,
        sell_ad=base.sell_ad,
        instruments=base.instruments,
        config=base.config,
        amount_cap=Decimal("Infinity"),
    )
    with pytest.raises(MarginInputError):
        service.evaluate(req)


def test_input_error_nan_fee_in_config(service: MarginService) -> None:
    cfg = MarginConfig.model_construct(
        **{**_cfg().model_dump(), "buy_fee_pct": Decimal("NaN")}
    )
    with pytest.raises(MarginInputError):
        service.evaluate(_request(config=cfg))


def test_build_config_missing_required(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.build_config({"min_net_margin_pct": "1"})
    with pytest.raises(MarginInputError):
        service.build_config({"max_deal_usdt": "100"})


def test_build_config_defaults(service: MarginService) -> None:
    cfg = service.build_config(
        {"min_net_margin_pct": "1.5", "max_deal_usdt": "200"}
    )
    assert cfg.buy_fee_pct == Decimal("0")
    assert cfg.sell_fee_pct == Decimal("0")
    assert cfg.fiat_cost_pct == Decimal("0")
    assert cfg.fees_verified is False
    assert cfg.min_counterparty_rating is None
    assert cfg.min_counterparty_orders is None
    assert cfg.min_net_margin_pct == Decimal("1.5")
    assert cfg.max_deal_usdt == Decimal("200")


def test_build_config_non_numeric_raises(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.build_config(
            {"min_net_margin_pct": "not-a-number", "max_deal_usdt": "100"}
        )


def test_input_error_negative_fee(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(config=_cfg(buy_fee_pct="-0.1", max_deal_usdt="100"))
        )


def test_input_error_fee_equal_100(service: MarginService) -> None:
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(config=_cfg(sell_fee_pct="100", max_deal_usdt="100"))
        )


def test_input_error_negative_min_counterparty_orders(
    service: MarginService,
) -> None:
    with pytest.raises(MarginInputError):
        service.evaluate(
            _request(config=_cfg(min_counterparty_orders=-1, max_deal_usdt="100"))
        )


# --- И: округление и большие числа ---


def test_round_crypto_down() -> None:
    assert round_crypto(Decimal("1.0000000000000000019")) == Decimal(
        "1.000000000000000001"
    )


def test_round_pct_half_up() -> None:
    assert round_pct(Decimal("1.2345675")) == Decimal("1.234568")


def test_large_numbers_no_invalid_operation(service: MarginService) -> None:
    amount = "1000000.123456789012345678"
    price_buy = "99999.12345678"
    price_sell = "99999.22345678"
    try:
        result = service.evaluate(
            _request(
                buy=_ad(
                    ad_snapshot_id=1,
                    side="sell",
                    price=price_buy,
                    available_amount=amount,
                    max_amount="999999999999",
                ),
                sell=_ad(
                    ad_snapshot_id=2,
                    counterparty_id=20,
                    side="buy",
                    price=price_sell,
                    available_amount=amount,
                    max_amount="999999999999",
                ),
                config=_cfg(max_deal_usdt=amount, min_net_margin_pct="-100"),
            )
        )
    except InvalidOperation as exc:
        pytest.fail(f"InvalidOperation: {exc}")
    assert result.amount_token is not None
    assert result.net_margin_pct is not None


# --- К: hypothesis ---


_finite_nonneg = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("100"),
    allow_nan=False,
    allow_infinity=False,
    places=6,
)
_finite_price = st.decimals(
    min_value=Decimal("1"),
    max_value=Decimal("1000"),
    allow_nan=False,
    allow_infinity=False,
    places=4,
)


@given(
    buy_fee=_finite_nonneg,
    sell_fee=_finite_nonneg,
    fiat_cost=_finite_nonneg,
    buy_price=_finite_price,
    sell_price=_finite_price,
)
@settings(derandomize=True, max_examples=50)
def test_k_net_margin_le_gross_when_fees_nonneg(
    buy_fee: Decimal,
    sell_fee: Decimal,
    fiat_cost: Decimal,
    buy_price: Decimal,
    sell_price: Decimal,
) -> None:
    service = MarginService()
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price=str(buy_price),
            available_amount="100",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price=str(sell_price),
            available_amount="100",
        ),
        config=_cfg(
            max_deal_usdt="100",
            buy_fee_pct=str(buy_fee),
            sell_fee_pct=str(sell_fee),
            fiat_cost_pct=str(fiat_cost),
            min_net_margin_pct="-1000000",
        ),
    )
    result = service.evaluate(req)
    assert result.net_margin_pct is not None
    assert result.gross_margin_pct is not None
    assert result.net_margin_pct <= result.gross_margin_pct


@given(buy_price=_finite_price, sell_price=_finite_price)
@settings(derandomize=True, max_examples=40)
def test_k_net_equals_gross_when_zero_fees(
    buy_price: Decimal, sell_price: Decimal
) -> None:
    service = MarginService()
    req = _request(
        buy=_ad(
            ad_snapshot_id=1,
            side="sell",
            price=str(buy_price),
            available_amount="50",
        ),
        sell=_ad(
            ad_snapshot_id=2,
            counterparty_id=20,
            side="buy",
            price=str(sell_price),
            available_amount="50",
        ),
        config=_cfg(max_deal_usdt="50", min_net_margin_pct="-1000000"),
    )
    result = service.evaluate(req)
    assert result.net_margin_pct == result.gross_margin_pct


# --- Dishka provider (отклонение: без container.py) ---


@pytest.mark.asyncio
async def test_margin_service_provider_resolves() -> None:
    container = make_async_container(MarginServiceProvider())
    async with container() as request_container:
        resolved: Any = await request_container.get(MarginService)
        assert isinstance(resolved, MarginService)
    await container.close()
