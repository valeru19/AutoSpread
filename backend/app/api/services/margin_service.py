"""Чистый расчёт маржи по паре объявлений (без БД и биржи)."""

from decimal import (
    ROUND_DOWN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    InvalidOperation,
    localcontext,
)
from typing import Any

from dishka import Provider, Scope, provide

from app.api.dto.margin import (
    AdInput,
    InstrumentInput,
    MarginConfig,
    MarginRequest,
    MarginResult,
)
from app.core.service_exceptions import MarginInputError

CALC_PREC = 50
_CALC_CONTEXT = Context(prec=CALC_PREC)

_CRYPTO_QUANT = Decimal("0.000000000000000001")
_FIAT_QUANT = Decimal("0.0001")
_PRICE_QUANT = Decimal("0.00000001")
_PCT_QUANT = Decimal("0.000001")

REJECT_CURRENCY_MISMATCH = "currency_mismatch"
REJECT_SAME_AD = "same_ad"
REJECT_BLACKLISTED = "blacklisted_counterparty"
REJECT_COUNTERPARTY_BELOW = "counterparty_below_threshold"
REJECT_NO_INSTRUMENT = "no_matching_instrument"
REJECT_EMPTY_INTERSECTION = "empty_intersection"
REJECT_BELOW_MIN_LIMIT = "below_min_limit"
REJECT_BELOW_MARGIN = "below_margin_threshold"

_ADVERTISER_SIDE_FOR_BUY_LEG = "sell"
_ADVERTISER_SIDE_FOR_SELL_LEG = "buy"


def round_crypto(value: Decimal) -> Decimal:
    """Округление crypto-суммы вниз до 18 знаков."""
    return value.quantize(_CRYPTO_QUANT, rounding=ROUND_DOWN)


def round_fiat(value: Decimal) -> Decimal:
    """Округление fiat до 4 знаков (HALF_UP)."""
    return value.quantize(_FIAT_QUANT, rounding=ROUND_HALF_UP)


def round_price(value: Decimal) -> Decimal:
    """Округление цены до 8 знаков (HALF_UP)."""
    return value.quantize(_PRICE_QUANT, rounding=ROUND_HALF_UP)


def round_pct(value: Decimal) -> Decimal:
    """Округление процента до 6 знаков (HALF_UP)."""
    return value.quantize(_PCT_QUANT, rounding=ROUND_HALF_UP)


def _dec_str(value: Decimal) -> str:
    """Преобразует Decimal в строку без экспоненциальной записи.

    :param value: число для сериализации
    :return: строковое представление
    """
    return format(value, "f")


def _require_finite(value: Decimal, field_name: str) -> None:
    """Проверяет, что Decimal конечный; иначе MarginInputError.

    :param value: проверяемое значение
    :param field_name: имя поля для сообщения об ошибке
    :return: None
    """
    if not value.is_finite():
        raise MarginInputError(f"Non-finite Decimal in {field_name}")


class MarginService:
    """Чистый расчёт чистой маржи по паре объявлений без БД и биржи.

    Нужен, чтобы CLI dry-run / сканер / FSM решали «принять/отклонить»
    по конфигу и входным DTO. Используется из CLI и (позже) из API/воркера
    через Dishka Provider.
    """

    def build_config(self, params: dict) -> MarginConfig:
        """Собирает MarginConfig из config_version.params.

        :param params: словарь params версии конфига
        :return: MarginConfig
        """
        if "min_net_margin_pct" not in params or "max_deal_usdt" not in params:
            raise MarginInputError(
                "params must contain min_net_margin_pct and max_deal_usdt"
            )

        try:
            buy_fee = params.get("buy_fee_pct", Decimal("0"))
            sell_fee = params.get("sell_fee_pct", Decimal("0"))
            fiat_cost = params.get("fiat_cost_pct", Decimal("0"))
            fees_verified = params.get("fees_verified", False)
            min_rating = params.get("min_counterparty_rating", None)
            min_orders = params.get("min_counterparty_orders", None)

            min_net = Decimal(str(params["min_net_margin_pct"]))
            max_deal = Decimal(str(params["max_deal_usdt"]))
            buy_fee_d = Decimal(str(buy_fee))
            sell_fee_d = Decimal(str(sell_fee))
            fiat_cost_d = Decimal(str(fiat_cost))
            min_rating_d = (
                None if min_rating is None else Decimal(str(min_rating))
            )
            min_orders_i = (
                None if min_orders is None else int(min_orders)
            )
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise MarginInputError(
                f"Invalid params value: {exc}"
            ) from exc

        for name, value in (
            ("min_net_margin_pct", min_net),
            ("max_deal_usdt", max_deal),
            ("buy_fee_pct", buy_fee_d),
            ("sell_fee_pct", sell_fee_d),
            ("fiat_cost_pct", fiat_cost_d),
            ("min_counterparty_rating", min_rating_d),
        ):
            if value is not None:
                _require_finite(value, f"params.{name}")

        return MarginConfig(
            min_net_margin_pct=min_net,
            max_deal_usdt=max_deal,
            buy_fee_pct=buy_fee_d,
            sell_fee_pct=sell_fee_d,
            fiat_cost_pct=fiat_cost_d,
            fees_verified=bool(fees_verified),
            min_counterparty_rating=min_rating_d,
            min_counterparty_orders=min_orders_i,
        )

    def evaluate(self, request: MarginRequest) -> MarginResult:
        """Оценивает пару buy/sell: принята ли сделка и с какими числами.

        Сопоставление method_code инструмента с payment_methods объявления —
        точное строковое сравнение без приведения регистра.

        :param request: объявления, инструменты, конфиг, опциональный amount_cap
        :return: MarginResult (accepted / reject_reason + числа или None)
        """
        with localcontext(_CALC_CONTEXT.copy()):
            return self._evaluate(request)

    def _evaluate(self, request: MarginRequest) -> MarginResult:
        """Выполняет проверки и расчёт маржи внутри локального decimal-контекста.

        :param request: входной запрос оценки
        :return: результат принятия или отказа
        """
        self._validate_input(request)

        buy = request.buy_ad
        sell = request.sell_ad
        cfg = request.config
        fees = self._fees_dict(cfg)
        calc_inputs = self._base_calc_inputs(request)

        if buy.currency != sell.currency:
            return self._reject(
                REJECT_CURRENCY_MISMATCH, cfg, fees, calc_inputs
            )

        if buy.ad_snapshot_id == sell.ad_snapshot_id:
            return self._reject(REJECT_SAME_AD, cfg, fees, calc_inputs)

        if buy.is_blacklisted or sell.is_blacklisted:
            return self._reject(REJECT_BLACKLISTED, cfg, fees, calc_inputs)

        if self._counterparty_below_threshold(buy, cfg) or (
            self._counterparty_below_threshold(sell, cfg)
        ):
            return self._reject(
                REJECT_COUNTERPARTY_BELOW, cfg, fees, calc_inputs
            )

        buy_instrument_id = self._match_instrument(buy, request.instruments)
        sell_instrument_id = self._match_instrument(sell, request.instruments)
        if buy_instrument_id is None or sell_instrument_id is None:
            return self._reject(REJECT_NO_INSTRUMENT, cfg, fees, calc_inputs)

        calc_inputs["buy_instrument_id"] = buy_instrument_id
        calc_inputs["sell_instrument_id"] = sell_instrument_id

        amount_token = self._compute_amount_token(request)
        calc_inputs["amount_token_raw"] = _dec_str(amount_token)
        if amount_token <= 0:
            return self._reject(
                REJECT_EMPTY_INTERSECTION,
                cfg,
                fees,
                calc_inputs,
                buy_instrument_id=buy_instrument_id,
                sell_instrument_id=sell_instrument_id,
            )

        buy_fiat = amount_token * buy.price
        sell_fiat = amount_token * sell.price
        if buy_fiat < buy.min_amount or sell_fiat < sell.min_amount:
            return self._reject(
                REJECT_BELOW_MIN_LIMIT,
                cfg,
                fees,
                calc_inputs,
                buy_instrument_id=buy_instrument_id,
                sell_instrument_id=sell_instrument_id,
            )

        buy_price = buy.price
        sell_price = sell.price
        amount = amount_token

        buy_notional = amount * buy_price
        buy_cost_raw = (
            buy_notional * (Decimal("1") + cfg.buy_fee_pct / Decimal("100"))
            + buy_notional * cfg.fiat_cost_pct / Decimal("100")
        )
        sell_revenue_raw = amount * sell_price * (
            Decimal("1") - cfg.sell_fee_pct / Decimal("100")
        )
        net_profit_raw = sell_revenue_raw - buy_cost_raw
        net_margin_raw = net_profit_raw / buy_cost_raw * Decimal("100")
        gross_margin_raw = (
            (sell_price - buy_price) / buy_price * Decimal("100")
        )

        buy_cost = round_fiat(buy_cost_raw)
        sell_revenue = round_fiat(sell_revenue_raw)
        net_profit_fiat = round_fiat(net_profit_raw)
        net_margin_pct = round_pct(net_margin_raw)
        gross_margin_pct = round_pct(gross_margin_raw)
        amount_out = round_crypto(amount)
        buy_price_out = round_price(buy_price)
        sell_price_out = round_price(sell_price)

        calc_inputs.update(
            {
                "amount_token": _dec_str(amount_out),
                "buy_price": _dec_str(buy_price_out),
                "sell_price": _dec_str(sell_price_out),
                "buy_fee_pct": _dec_str(cfg.buy_fee_pct),
                "sell_fee_pct": _dec_str(cfg.sell_fee_pct),
                "fiat_cost_pct": _dec_str(cfg.fiat_cost_pct),
            }
        )

        if net_margin_pct < cfg.min_net_margin_pct:
            return MarginResult(
                accepted=False,
                reject_reason=REJECT_BELOW_MARGIN,
                amount_token=amount_out,
                buy_price=buy_price_out,
                sell_price=sell_price_out,
                buy_cost=buy_cost,
                sell_revenue=sell_revenue,
                net_profit_fiat=net_profit_fiat,
                gross_margin_pct=gross_margin_pct,
                net_margin_pct=net_margin_pct,
                buy_instrument_id=buy_instrument_id,
                sell_instrument_id=sell_instrument_id,
                fees_verified=cfg.fees_verified,
                fees=fees,
                calc_inputs=calc_inputs,
            )

        return MarginResult(
            accepted=True,
            reject_reason=None,
            amount_token=amount_out,
            buy_price=buy_price_out,
            sell_price=sell_price_out,
            buy_cost=buy_cost,
            sell_revenue=sell_revenue,
            net_profit_fiat=net_profit_fiat,
            gross_margin_pct=gross_margin_pct,
            net_margin_pct=net_margin_pct,
            buy_instrument_id=buy_instrument_id,
            sell_instrument_id=sell_instrument_id,
            fees_verified=cfg.fees_verified,
            fees=fees,
            calc_inputs=calc_inputs,
        )

    def _validate_input(self, request: MarginRequest) -> None:
        """Проверяет стороны, конечность Decimal и допустимость лимитов/комиссий.

        :param request: входной запрос
        :return: None
        """
        buy = request.buy_ad
        sell = request.sell_ad
        cfg = request.config

        if buy.side != _ADVERTISER_SIDE_FOR_BUY_LEG:
            raise MarginInputError(
                'buy_ad.side must be "sell" (advertiser side)'
            )
        if sell.side != _ADVERTISER_SIDE_FOR_SELL_LEG:
            raise MarginInputError(
                'sell_ad.side must be "buy" (advertiser side)'
            )

        decimal_fields: list[tuple[str, Decimal | None]] = [
            ("buy_ad.price", buy.price),
            ("buy_ad.available_amount", buy.available_amount),
            ("buy_ad.min_amount", buy.min_amount),
            ("buy_ad.max_amount", buy.max_amount),
            ("buy_ad.rating", buy.rating),
            ("sell_ad.price", sell.price),
            ("sell_ad.available_amount", sell.available_amount),
            ("sell_ad.min_amount", sell.min_amount),
            ("sell_ad.max_amount", sell.max_amount),
            ("sell_ad.rating", sell.rating),
            ("config.min_net_margin_pct", cfg.min_net_margin_pct),
            ("config.max_deal_usdt", cfg.max_deal_usdt),
            ("config.buy_fee_pct", cfg.buy_fee_pct),
            ("config.sell_fee_pct", cfg.sell_fee_pct),
            ("config.fiat_cost_pct", cfg.fiat_cost_pct),
            ("config.min_counterparty_rating", cfg.min_counterparty_rating),
            ("amount_cap", request.amount_cap),
        ]
        for name, value in decimal_fields:
            if value is not None:
                _require_finite(value, name)

        for label, ad in (("buy_ad", buy), ("sell_ad", sell)):
            if ad.price <= 0:
                raise MarginInputError(f"{label}.price must be > 0")
            if ad.available_amount < 0:
                raise MarginInputError(
                    f"{label}.available_amount must be >= 0"
                )
            if ad.min_amount < 0:
                raise MarginInputError(f"{label}.min_amount must be >= 0")
            if ad.max_amount < 0:
                raise MarginInputError(f"{label}.max_amount must be >= 0")

        if request.amount_cap is not None and request.amount_cap <= 0:
            raise MarginInputError("amount_cap must be > 0 when set")

        for fee_name, fee_value in (
            ("buy_fee_pct", cfg.buy_fee_pct),
            ("sell_fee_pct", cfg.sell_fee_pct),
            ("fiat_cost_pct", cfg.fiat_cost_pct),
        ):
            if fee_value < 0 or fee_value >= 100:
                raise MarginInputError(
                    f"config.{fee_name} must be >= 0 and < 100"
                )

        if (
            cfg.min_counterparty_orders is not None
            and cfg.min_counterparty_orders < 0
        ):
            raise MarginInputError(
                "config.min_counterparty_orders must be >= 0"
            )

    def _counterparty_below_threshold(
        self, ad: AdInput, cfg: MarginConfig
    ) -> bool:
        """Проверяет, что контрагент объявления ниже заданных порогов.

        :param ad: объявление с полями контрагента
        :param cfg: конфиг с порогами (None = не применять)
        :return: True, если контрагент ниже порога
        """
        if (
            cfg.min_counterparty_rating is not None
            and ad.rating is not None
            and ad.rating < cfg.min_counterparty_rating
        ):
            return True
        if (
            cfg.min_counterparty_orders is not None
            and ad.orders_count is not None
            and ad.orders_count < cfg.min_counterparty_orders
        ):
            return True
        return False

    def _match_instrument(
        self, ad: AdInput, instruments: list[InstrumentInput]
    ) -> int | None:
        """Подбирает активный инструмент: валюта и method_code (точное сравнение).

        :param ad: объявление с currency и payment_methods
        :param instruments: список доступных инструментов
        :return: наименьший instrument_id или None
        """
        matched: list[int] = []
        for inst in instruments:
            if not inst.is_active:
                continue
            if inst.currency != ad.currency:
                continue
            if inst.method_code not in ad.payment_methods:
                continue
            matched.append(inst.instrument_id)
        if not matched:
            return None
        return min(matched)

    def _compute_amount_token(self, request: MarginRequest) -> Decimal:
        """Считает amount_token как минимум из пяти ограничений, ROUND_DOWN 18.

        :param request: запрос с объявлениями, конфигом и amount_cap
        :return: объём в токене (может быть <= 0)
        """
        buy = request.buy_ad
        sell = request.sell_ad
        cap = (
            request.amount_cap
            if request.amount_cap is not None
            else request.config.max_deal_usdt
        )
        candidates = [
            buy.available_amount,
            sell.available_amount,
            cap,
            buy.max_amount / buy.price,
            sell.max_amount / sell.price,
        ]
        return round_crypto(min(candidates))

    def _fees_dict(self, cfg: MarginConfig) -> dict[str, str]:
        """Собирает словарь комиссий для MarginResult.fees.

        :param cfg: конфиг с процентами комиссий
        :return: dict[str, str] с buy/sell/fiat fee
        """
        return {
            "buy_fee_pct": _dec_str(cfg.buy_fee_pct),
            "sell_fee_pct": _dec_str(cfg.sell_fee_pct),
            "fiat_cost_pct": _dec_str(cfg.fiat_cost_pct),
        }

    def _base_calc_inputs(self, request: MarginRequest) -> dict[str, Any]:
        """Собирает JSON-совместимые входы расчёта (Decimal как str).

        :param request: входной запрос
        :return: словарь calc_inputs
        """
        buy = request.buy_ad
        sell = request.sell_ad
        cfg = request.config
        return {
            "buy_ad_snapshot_id": buy.ad_snapshot_id,
            "sell_ad_snapshot_id": sell.ad_snapshot_id,
            "buy_price": _dec_str(buy.price),
            "sell_price": _dec_str(sell.price),
            "buy_available_amount": _dec_str(buy.available_amount),
            "sell_available_amount": _dec_str(sell.available_amount),
            "buy_min_amount": _dec_str(buy.min_amount),
            "sell_min_amount": _dec_str(sell.min_amount),
            "buy_max_amount": _dec_str(buy.max_amount),
            "sell_max_amount": _dec_str(sell.max_amount),
            "max_deal_usdt": _dec_str(cfg.max_deal_usdt),
            "amount_cap": (
                None
                if request.amount_cap is None
                else _dec_str(request.amount_cap)
            ),
            "buy_fee_pct": _dec_str(cfg.buy_fee_pct),
            "sell_fee_pct": _dec_str(cfg.sell_fee_pct),
            "fiat_cost_pct": _dec_str(cfg.fiat_cost_pct),
            "min_net_margin_pct": _dec_str(cfg.min_net_margin_pct),
        }

    def _reject(
        self,
        reason: str,
        cfg: MarginConfig,
        fees: dict[str, str],
        calc_inputs: dict[str, Any],
        *,
        buy_instrument_id: int | None = None,
        sell_instrument_id: int | None = None,
    ) -> MarginResult:
        """Собирает отказ до расчёта: числовые поля None.

        :param reason: код reject_reason
        :param cfg: конфиг (fees_verified)
        :param fees: уже собранный словарь комиссий
        :param calc_inputs: входы для аудита
        :param buy_instrument_id: id buy-инструмента, если уже найден
        :param sell_instrument_id: id sell-инструмента, если уже найден
        :return: MarginResult с accepted=False
        """
        # ***reason: код бизнес-отказа (не MarginInputError)***
        # ***cfg: источник fees_verified***
        # ***fees / calc_inputs: сериализованный след входа***
        # ***buy_instrument_id / sell_instrument_id: заполняются после match***
        return MarginResult(
            accepted=False,
            reject_reason=reason,
            amount_token=None,
            buy_price=None,
            sell_price=None,
            buy_cost=None,
            sell_revenue=None,
            net_profit_fiat=None,
            gross_margin_pct=None,
            net_margin_pct=None,
            buy_instrument_id=buy_instrument_id,
            sell_instrument_id=sell_instrument_id,
            fees_verified=cfg.fees_verified,
            fees=fees,
            calc_inputs=calc_inputs,
        )


class MarginServiceProvider(Provider):
    """Dishka-провайдер MarginService (без session / БД)."""

    @provide(scope=Scope.REQUEST)
    def margin_service(self) -> MarginService:
        """Создаёт MarginService без зависимостей.

        :return: экземпляр MarginService
        """
        return MarginService()
