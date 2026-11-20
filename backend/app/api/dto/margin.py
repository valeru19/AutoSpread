"""DTO входа и выхода MarginService."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AdInput(BaseModel):
    """Объявление + поля контрагента для оценки маржи."""

    ad_snapshot_id: int
    counterparty_id: int
    currency: str
    side: str
    price: Decimal
    available_amount: Decimal
    min_amount: Decimal
    max_amount: Decimal
    payment_methods: list[str]
    is_blacklisted: bool
    rating: Decimal | None
    orders_count: int | None


class InstrumentInput(BaseModel):
    """Платёжный инструмент для сопоставления с методами объявления."""

    instrument_id: int
    currency: str
    method_code: str
    is_active: bool


class MarginConfig(BaseModel):
    """Параметры риска и комиссий для расчёта маржи."""

    min_net_margin_pct: Decimal
    max_deal_usdt: Decimal
    buy_fee_pct: Decimal
    sell_fee_pct: Decimal
    fiat_cost_pct: Decimal
    fees_verified: bool
    min_counterparty_rating: Decimal | None
    min_counterparty_orders: int | None


class MarginRequest(BaseModel):
    """Запрос оценки пары buy/sell объявлений."""

    buy_ad: AdInput
    sell_ad: AdInput
    instruments: list[InstrumentInput]
    config: MarginConfig
    amount_cap: Decimal | None = None


class MarginResult(BaseModel):
    """Результат оценки: принято/отклонено и числа расчёта."""

    accepted: bool
    reject_reason: str | None
    amount_token: Decimal | None
    buy_price: Decimal | None
    sell_price: Decimal | None
    buy_cost: Decimal | None
    sell_revenue: Decimal | None
    net_profit_fiat: Decimal | None
    gross_margin_pct: Decimal | None
    net_margin_pct: Decimal | None
    buy_instrument_id: int | None
    sell_instrument_id: int | None
    fees_verified: bool
    fees: dict[str, str]
    calc_inputs: dict[str, Any] = Field(default_factory=dict)
