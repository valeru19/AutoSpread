"""Чистый FSM сделки: (state, event) → new_state + effects без БД."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from dishka import Provider, Scope, provide

from app.api.dto.deal_fsm import FsmContext, FsmEffect, FsmEvent, FsmResult
from app.core.service_exceptions import (
    ConcurrentModificationError,
    InvalidTransitionError,
    KillSwitchError,
    ReceiptRequired,
)

# --- состояния ---
STATE_OPPORTUNITY = "opportunity"
STATE_AWAITING_OPEN_ACK = "awaiting_open_ack"
STATE_BUY_ORDER = "buy_order"
STATE_AWAITING_PAY_ACK = "awaiting_pay_ack"
STATE_MARK_PAID = "mark_paid"
STATE_AWAITING_CRYPTO = "awaiting_crypto"
STATE_SELL_ORDER = "sell_order"
STATE_AWAITING_INCOMING = "awaiting_incoming"
STATE_AWAITING_RELEASE_ACK = "awaiting_release_ack"
STATE_RELEASED = "released"
STATE_CLOSED = "closed"
STATE_CANCELLED = "cancelled"
STATE_DISPUTE = "dispute"

STATES: frozenset[str] = frozenset(
    {
        STATE_OPPORTUNITY,
        STATE_AWAITING_OPEN_ACK,
        STATE_BUY_ORDER,
        STATE_AWAITING_PAY_ACK,
        STATE_MARK_PAID,
        STATE_AWAITING_CRYPTO,
        STATE_SELL_ORDER,
        STATE_AWAITING_INCOMING,
        STATE_AWAITING_RELEASE_ACK,
        STATE_RELEASED,
        STATE_CLOSED,
        STATE_CANCELLED,
        STATE_DISPUTE,
    }
)

TERMINAL_STATES: frozenset[str] = frozenset(
    {STATE_CLOSED, STATE_CANCELLED, STATE_DISPUTE}
)

# --- события ---
EVENT_TAKE = "take"
EVENT_ACK_OPEN = "ack_open"
EVENT_REJECT = "reject"
EVENT_TIMEOUT = "timeout"
EVENT_PAYMENT_OUT_READY = "payment_out_ready"
EVENT_ACK_PAY = "ack_pay"
EVENT_MARK_PAID_CONFIRMED = "mark_paid_confirmed"
EVENT_CRYPTO_RECEIVED = "crypto_received"
EVENT_SELL_ORDER_CREATED = "sell_order_created"
EVENT_PAYMENT_MATCHED = "payment_matched"
EVENT_ACK_RELEASE = "ack_release"
EVENT_RELEASE_CONFIRMED = "release_confirmed"
EVENT_DISPUTE_OPENED = "dispute_opened"

EVENTS: frozenset[str] = frozenset(
    {
        EVENT_TAKE,
        EVENT_ACK_OPEN,
        EVENT_REJECT,
        EVENT_TIMEOUT,
        EVENT_PAYMENT_OUT_READY,
        EVENT_ACK_PAY,
        EVENT_MARK_PAID_CONFIRMED,
        EVENT_CRYPTO_RECEIVED,
        EVENT_SELL_ORDER_CREATED,
        EVENT_PAYMENT_MATCHED,
        EVENT_ACK_RELEASE,
        EVENT_RELEASE_CONFIRMED,
        EVENT_DISPUTE_OPENED,
    }
)

# --- виды эффектов ---
EFFECT_NOTIFY = "notify"
EFFECT_CREATE_ORDER = "create_order"
EFFECT_CANCEL_ORDER = "cancel_order"
EFFECT_MARK_PAID = "mark_paid"
EFFECT_RELEASE = "release"
EFFECT_REMIND = "remind"
EFFECT_AUDIT = "audit"
EFFECT_RECORD_PNL = "record_pnl"
EFFECT_ALERT_OPERATOR = "alert_operator"

# --- аргументы эффектов ---
ARG_BUY = "buy"
ARG_SELL = "sell"
ARG_ACK_OPEN = "ack_open"
ARG_ACK_PAY = "ack_pay"
ARG_ACK_RELEASE = "ack_release"
ARG_RECHECK_FAILED = "recheck_failed"
ARG_OPEN_TIMEOUT = "open_timeout"
ARG_BUY_TIMEOUT = "buy_timeout"
ARG_SELL_ORDER_CREATED = "sell_order_created"
ARG_RELEASE_REJECTED = "release_rejected"
ARG_DISPUTE = "dispute"
ARG_DISPUTE_OPENED = "dispute_opened"
ARG_KILL_SWITCH = "kill_switch"
ARG_OPERATOR_REJECT = "operator_reject"
ARG_CRYPTO = "crypto"

RuleHandler = Callable[[FsmContext, FsmEvent, datetime], FsmResult]


@dataclass(frozen=True)
class TransitionRule:
    """Одна строка таблицы переходов: обработчик пары (state, event)."""

    run: RuleHandler


def _effect(kind: str, arg: str | None = None) -> FsmEffect:
    """Создаёт FsmEffect.

    :param kind: вид эффекта
    :param arg: строковый аргумент или None
    :return: FsmEffect
    """
    return FsmEffect(kind=kind, arg=arg)


def _result(
    context: FsmContext,
    new_state: str,
    effects: list[FsmEffect],
) -> FsmResult:
    """Собирает FsmResult с инкрементом row_version только при смене state.

    :param context: текущий контекст
    :param new_state: целевое состояние
    :param effects: список эффектов
    :return: FsmResult (duplicate=False)
    """
    # ***context: источник текущего state/row_version***
    # ***new_state: следующее состояние***
    # ***effects: побочные эффекты оркестратору***
    new_version = (
        context.row_version + 1
        if new_state != context.state
        else context.row_version
    )
    return FsmResult(
        new_state=new_state,
        new_row_version=new_version,
        effects=effects,
        duplicate=False,
    )


def _is_aware(value: datetime) -> bool:
    """Проверяет, что datetime aware (tzinfo и utcoffset заданы).

    :param value: момент времени
    :return: True, если aware
    """
    return value.tzinfo is not None and value.utcoffset() is not None


def _ensure_timeout_due(context: FsmContext, now: datetime) -> None:
    """Проверяет допустимость timeout: aware и now >= deadline.

    :param context: контекст с state_deadline_at
    :param now: момент проверки
    :return: None
    """
    deadline = context.state_deadline_at
    if deadline is None:
        raise InvalidTransitionError("timeout without state_deadline_at")
    if not _is_aware(now):
        raise InvalidTransitionError("now must be timezone-aware")
    if not _is_aware(deadline):
        raise InvalidTransitionError("state_deadline_at must be timezone-aware")
    if now < deadline:
        raise InvalidTransitionError("timeout before state_deadline_at")


def _on_opportunity_take(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """take из opportunity: ack или сразу buy_order.

    :param context: контекст сделки
    :param event: событие take
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    if context.require_ack_open:
        return _result(
            context,
            STATE_AWAITING_OPEN_ACK,
            [_effect(EFFECT_NOTIFY, ARG_ACK_OPEN)],
        )
    return _result(
        context,
        STATE_BUY_ORDER,
        [_effect(EFFECT_CREATE_ORDER, ARG_BUY)],
    )


def _on_awaiting_open_ack_ack_open(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """ack_open: recheck_passed обязателен.

    :param context: контекст
    :param event: событие с recheck_passed
    :param now: не используется
    :return: FsmResult
    """
    del now
    if event.recheck_passed is None:
        raise InvalidTransitionError("ack_open requires recheck_passed")
    if event.recheck_passed is True:
        return _result(
            context,
            STATE_BUY_ORDER,
            [_effect(EFFECT_CREATE_ORDER, ARG_BUY)],
        )
    return _result(
        context,
        STATE_CANCELLED,
        [
            _effect(EFFECT_NOTIFY, ARG_RECHECK_FAILED),
            _effect(EFFECT_AUDIT, ARG_RECHECK_FAILED),
        ],
    )


def _on_awaiting_open_ack_reject(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """reject из awaiting_open_ack → cancelled.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_CANCELLED,
        [_effect(EFFECT_AUDIT, ARG_OPERATOR_REJECT)],
    )


def _on_awaiting_open_ack_timeout(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """timeout из awaiting_open_ack → cancelled.

    :param context: контекст
    :param event: событие
    :param now: момент для проверки deadline
    :return: FsmResult
    """
    del event
    _ensure_timeout_due(context, now)
    return _result(
        context,
        STATE_CANCELLED,
        [_effect(EFFECT_NOTIFY, ARG_OPEN_TIMEOUT)],
    )


def _on_buy_order_payment_out_ready(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """payment_out_ready из buy_order: чек обязателен.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    if not context.has_receipt_out:
        raise ReceiptRequired("payment_out_ready requires has_receipt_out")
    if context.require_ack_pay:
        return _result(
            context,
            STATE_AWAITING_PAY_ACK,
            [_effect(EFFECT_NOTIFY, ARG_ACK_PAY)],
        )
    return _result(
        context,
        STATE_MARK_PAID,
        [_effect(EFFECT_MARK_PAID)],
    )


def _on_buy_order_timeout(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """timeout из buy_order → cancelled + cancel_order(buy).

    :param context: контекст
    :param event: событие
    :param now: момент для deadline
    :return: FsmResult
    """
    del event
    _ensure_timeout_due(context, now)
    return _result(
        context,
        STATE_CANCELLED,
        [
            _effect(EFFECT_CANCEL_ORDER, ARG_BUY),
            _effect(EFFECT_NOTIFY, ARG_BUY_TIMEOUT),
        ],
    )


def _on_awaiting_pay_ack_ack_pay(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """ack_pay: нужен has_receipt_out.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    if not context.has_receipt_out:
        raise ReceiptRequired("ack_pay requires has_receipt_out")
    return _result(
        context,
        STATE_MARK_PAID,
        [_effect(EFFECT_MARK_PAID)],
    )


def _on_awaiting_pay_ack_reject(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """reject из awaiting_pay_ack → buy_order.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_BUY_ORDER,
        [_effect(EFFECT_AUDIT, ARG_OPERATOR_REJECT)],
    )


def _on_awaiting_pay_ack_timeout(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """timeout: remind, состояние не меняется.

    :param context: контекст
    :param event: событие
    :param now: момент для deadline
    :return: FsmResult
    """
    del event
    _ensure_timeout_due(context, now)
    return _result(
        context,
        STATE_AWAITING_PAY_ACK,
        [_effect(EFFECT_REMIND, ARG_ACK_PAY)],
    )


def _on_mark_paid_confirmed(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """mark_paid_confirmed → awaiting_crypto.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(context, STATE_AWAITING_CRYPTO, [])


def _on_awaiting_crypto_received(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """crypto_received → sell_order.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_SELL_ORDER,
        [_effect(EFFECT_CREATE_ORDER, ARG_SELL)],
    )


def _on_awaiting_crypto_timeout(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """timeout: remind crypto.

    :param context: контекст
    :param event: событие
    :param now: момент для deadline
    :return: FsmResult
    """
    del event
    _ensure_timeout_due(context, now)
    return _result(
        context,
        STATE_AWAITING_CRYPTO,
        [_effect(EFFECT_REMIND, ARG_CRYPTO)],
    )


def _on_sell_order_created(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """sell_order_created → awaiting_incoming.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_AWAITING_INCOMING,
        [_effect(EFFECT_NOTIFY, ARG_SELL_ORDER_CREATED)],
    )


def _on_awaiting_incoming_payment_matched(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """payment_matched: нужен has_receipt_in.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    if not context.has_receipt_in:
        raise ReceiptRequired("payment_matched requires has_receipt_in")
    if context.require_ack_release:
        return _result(
            context,
            STATE_AWAITING_RELEASE_ACK,
            [_effect(EFFECT_NOTIFY, ARG_ACK_RELEASE)],
        )
    return _result(
        context,
        STATE_RELEASED,
        [_effect(EFFECT_RELEASE)],
    )


def _on_awaiting_release_ack_ack_release(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """ack_release: чек и payment_matched обязательны.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    if not context.has_receipt_in:
        raise ReceiptRequired("ack_release requires has_receipt_in")
    if not context.payment_matched:
        raise InvalidTransitionError(
            "ack_release requires payment_matched"
        )
    return _result(
        context,
        STATE_RELEASED,
        [_effect(EFFECT_RELEASE)],
    )


def _on_awaiting_release_ack_reject(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """reject: остаёмся, notify release_rejected.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_AWAITING_RELEASE_ACK,
        [_effect(EFFECT_NOTIFY, ARG_RELEASE_REJECTED)],
    )


def _on_awaiting_release_ack_timeout(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """timeout: remind ack_release.

    :param context: контекст
    :param event: событие
    :param now: момент для deadline
    :return: FsmResult
    """
    del event
    _ensure_timeout_due(context, now)
    return _result(
        context,
        STATE_AWAITING_RELEASE_ACK,
        [_effect(EFFECT_REMIND, ARG_ACK_RELEASE)],
    )


def _on_released_release_confirmed(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """release_confirmed → closed + record_pnl.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_CLOSED,
        [_effect(EFFECT_RECORD_PNL)],
    )


def _on_dispute_opened(
    context: FsmContext, event: FsmEvent, now: datetime
) -> FsmResult:
    """dispute_opened из любого нетерминального → dispute.

    :param context: контекст
    :param event: событие
    :param now: не используется
    :return: FsmResult
    """
    del event, now
    return _result(
        context,
        STATE_DISPUTE,
        [
            _effect(EFFECT_NOTIFY, ARG_DISPUTE),
            _effect(EFFECT_AUDIT, ARG_DISPUTE_OPENED),
        ],
    )


# Таблица: по одной строке на пару (state, event). dispute_opened — отдельно.
TRANSITIONS: dict[tuple[str, str], TransitionRule] = {
    (STATE_OPPORTUNITY, EVENT_TAKE): TransitionRule(_on_opportunity_take),
    (STATE_AWAITING_OPEN_ACK, EVENT_ACK_OPEN): TransitionRule(
        _on_awaiting_open_ack_ack_open
    ),
    (STATE_AWAITING_OPEN_ACK, EVENT_REJECT): TransitionRule(
        _on_awaiting_open_ack_reject
    ),
    (STATE_AWAITING_OPEN_ACK, EVENT_TIMEOUT): TransitionRule(
        _on_awaiting_open_ack_timeout
    ),
    (STATE_BUY_ORDER, EVENT_PAYMENT_OUT_READY): TransitionRule(
        _on_buy_order_payment_out_ready
    ),
    (STATE_BUY_ORDER, EVENT_TIMEOUT): TransitionRule(_on_buy_order_timeout),
    (STATE_AWAITING_PAY_ACK, EVENT_ACK_PAY): TransitionRule(
        _on_awaiting_pay_ack_ack_pay
    ),
    (STATE_AWAITING_PAY_ACK, EVENT_REJECT): TransitionRule(
        _on_awaiting_pay_ack_reject
    ),
    (STATE_AWAITING_PAY_ACK, EVENT_TIMEOUT): TransitionRule(
        _on_awaiting_pay_ack_timeout
    ),
    (STATE_MARK_PAID, EVENT_MARK_PAID_CONFIRMED): TransitionRule(
        _on_mark_paid_confirmed
    ),
    (STATE_AWAITING_CRYPTO, EVENT_CRYPTO_RECEIVED): TransitionRule(
        _on_awaiting_crypto_received
    ),
    (STATE_AWAITING_CRYPTO, EVENT_TIMEOUT): TransitionRule(
        _on_awaiting_crypto_timeout
    ),
    (STATE_SELL_ORDER, EVENT_SELL_ORDER_CREATED): TransitionRule(
        _on_sell_order_created
    ),
    (STATE_AWAITING_INCOMING, EVENT_PAYMENT_MATCHED): TransitionRule(
        _on_awaiting_incoming_payment_matched
    ),
    (STATE_AWAITING_RELEASE_ACK, EVENT_ACK_RELEASE): TransitionRule(
        _on_awaiting_release_ack_ack_release
    ),
    (STATE_AWAITING_RELEASE_ACK, EVENT_REJECT): TransitionRule(
        _on_awaiting_release_ack_reject
    ),
    (STATE_AWAITING_RELEASE_ACK, EVENT_TIMEOUT): TransitionRule(
        _on_awaiting_release_ack_timeout
    ),
    (STATE_RELEASED, EVENT_RELEASE_CONFIRMED): TransitionRule(
        _on_released_release_confirmed
    ),
}

DISPUTE_RULE = TransitionRule(_on_dispute_opened)

_FREEZE_AFTER_BUY: frozenset[str] = frozenset(
    {
        STATE_AWAITING_PAY_ACK,
        STATE_MARK_PAID,
        STATE_AWAITING_CRYPTO,
        STATE_SELL_ORDER,
        STATE_AWAITING_INCOMING,
        STATE_AWAITING_RELEASE_ACK,
        STATE_RELEASED,
    }
)


class DealFsmService:
    """Чистый автомат состояний сделки без БД и побочных записей.

    Принимает контекст и событие, возвращает новое состояние и effects.
    Используется оркестратором / ack-роутами / worker (позже).
    """

    def transition(
        self,
        context: FsmContext,
        event: FsmEvent,
        now: datetime,
    ) -> FsmResult:
        """Применяет одно событие к контексту сделки.

        :param context: текущее состояние и флаги
        :param event: имя, id, row_version, recheck_passed
        :param now: момент проверки timeout (без datetime.now внутри)
        :return: FsmResult
        """
        # ***context: снимок сделки***
        # ***event: входящее событие***
        # ***now: внешние часы для timeout***
        if context.state not in STATES or event.name not in EVENTS:
            raise InvalidTransitionError("unknown state or event")

        if event.event_id in context.processed_event_ids:
            return FsmResult(
                new_state=context.state,
                new_row_version=context.row_version,
                effects=[],
                duplicate=True,
            )

        if event.row_version != context.row_version:
            raise ConcurrentModificationError(
                "event.row_version != context.row_version"
            )

        if context.state in TERMINAL_STATES:
            raise InvalidTransitionError("terminal state")

        rule = self._lookup_rule(context.state, event.name)
        if rule is None:
            raise InvalidTransitionError(
                f"no transition for ({context.state}, {event.name})"
            )

        if context.kill_switch and event.name != EVENT_DISPUTE_OPENED:
            return self._apply_kill_switch(context, event)

        return rule.run(context, event, now)

    def _lookup_rule(
        self, state: str, event_name: str
    ) -> TransitionRule | None:
        """Ищет правило таблицы для пары (state, event).

        :param state: текущее состояние
        :param event_name: имя события
        :return: TransitionRule или None
        """
        if event_name == EVENT_DISPUTE_OPENED:
            return DISPUTE_RULE
        return TRANSITIONS.get((state, event_name))

    def _apply_kill_switch(
        self, context: FsmContext, event: FsmEvent
    ) -> FsmResult:
        """Подменяет исход при kill_switch=True (пара уже в таблице).

        :param context: контекст
        :param event: событие
        :return: FsmResult или raises KillSwitchError
        """
        state = context.state
        name = event.name

        if state == STATE_AWAITING_OPEN_ACK and name == EVENT_ACK_OPEN:
            raise KillSwitchError("ack_open blocked by kill switch")

        if state in {STATE_OPPORTUNITY, STATE_AWAITING_OPEN_ACK}:
            return _result(
                context,
                STATE_CANCELLED,
                [_effect(EFFECT_AUDIT, ARG_KILL_SWITCH)],
            )

        if state == STATE_BUY_ORDER and name == EVENT_PAYMENT_OUT_READY:
            return _result(
                context,
                STATE_BUY_ORDER,
                [_effect(EFFECT_ALERT_OPERATOR, ARG_KILL_SWITCH)],
            )

        if state == STATE_BUY_ORDER:
            return _result(
                context,
                STATE_CANCELLED,
                [
                    _effect(EFFECT_CANCEL_ORDER, ARG_BUY),
                    _effect(EFFECT_NOTIFY, ARG_KILL_SWITCH),
                    _effect(EFFECT_AUDIT, ARG_KILL_SWITCH),
                ],
            )

        if state in _FREEZE_AFTER_BUY:
            return _result(
                context,
                state,
                [_effect(EFFECT_ALERT_OPERATOR, ARG_KILL_SWITCH)],
            )

        raise InvalidTransitionError(
            f"kill switch unhandled for ({state}, {name})"
        )


class DealFsmServiceProvider(Provider):
    """Dishka-провайдер DealFsmService (без session / БД)."""

    @provide(scope=Scope.REQUEST)
    def deal_fsm_service(self) -> DealFsmService:
        """Создаёт DealFsmService без зависимостей.

        :return: экземпляр DealFsmService
        """
        return DealFsmService()
