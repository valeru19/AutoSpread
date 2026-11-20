"""Тесты DealFsmService: таблица, идемпотентность, kill switch, сквозные пути."""

from datetime import UTC, datetime
from typing import Any

import pytest
from dishka import make_async_container

from app.api.dto.deal_fsm import FsmContext, FsmEffect, FsmEvent
from app.api.services.deal_fsm_service import DealFsmService, DealFsmServiceProvider
from app.core.service_exceptions import (
    ConcurrentModificationError,
    InvalidTransitionError,
    KillSwitchError,
    ReceiptRequired,
)

# Литерал допустимых пар (НЕ импорт из сервиса) — для теста Б.
_STATES = (
    "opportunity",
    "awaiting_open_ack",
    "buy_order",
    "awaiting_pay_ack",
    "mark_paid",
    "awaiting_crypto",
    "sell_order",
    "awaiting_incoming",
    "awaiting_release_ack",
    "released",
    "closed",
    "cancelled",
    "dispute",
)
_EVENTS = (
    "take",
    "ack_open",
    "reject",
    "timeout",
    "payment_out_ready",
    "ack_pay",
    "mark_paid_confirmed",
    "crypto_received",
    "sell_order_created",
    "payment_matched",
    "ack_release",
    "release_confirmed",
    "dispute_opened",
)
_TERMINAL = frozenset({"closed", "cancelled", "dispute"})
_ALLOWED_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("opportunity", "take"),
        ("awaiting_open_ack", "ack_open"),
        ("awaiting_open_ack", "reject"),
        ("awaiting_open_ack", "timeout"),
        ("buy_order", "payment_out_ready"),
        ("buy_order", "timeout"),
        ("awaiting_pay_ack", "ack_pay"),
        ("awaiting_pay_ack", "reject"),
        ("awaiting_pay_ack", "timeout"),
        ("mark_paid", "mark_paid_confirmed"),
        ("awaiting_crypto", "crypto_received"),
        ("awaiting_crypto", "timeout"),
        ("sell_order", "sell_order_created"),
        ("awaiting_incoming", "payment_matched"),
        ("awaiting_release_ack", "ack_release"),
        ("awaiting_release_ack", "reject"),
        ("awaiting_release_ack", "timeout"),
        ("released", "release_confirmed"),
        # dispute_opened из любого нетерминального
        *(
            (st, "dispute_opened")
            for st in _STATES
            if st not in _TERMINAL
        ),
    }
)
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_DEADLINE_PAST = datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC)
_DEADLINE_FUTURE = datetime(2026, 1, 1, 13, 0, 0, tzinfo=UTC)


def _ctx(
    *,
    state: str = "opportunity",
    row_version: int = 1,
    require_ack_open: bool = False,
    require_ack_pay: bool = False,
    require_ack_release: bool = False,
    has_receipt_out: bool = True,
    has_receipt_in: bool = True,
    payment_matched: bool = True,
    kill_switch: bool = False,
    processed_event_ids: frozenset[str] | None = None,
    state_deadline_at: datetime | None = None,
) -> FsmContext:
    return FsmContext(
        state=state,
        row_version=row_version,
        require_ack_open=require_ack_open,
        require_ack_pay=require_ack_pay,
        require_ack_release=require_ack_release,
        has_receipt_out=has_receipt_out,
        has_receipt_in=has_receipt_in,
        payment_matched=payment_matched,
        kill_switch=kill_switch,
        processed_event_ids=processed_event_ids or frozenset(),
        state_deadline_at=state_deadline_at,
    )


def _ev(
    name: str,
    *,
    event_id: str = "e1",
    row_version: int = 1,
    recheck_passed: bool | None = None,
) -> FsmEvent:
    return FsmEvent(
        name=name,
        event_id=event_id,
        row_version=row_version,
        recheck_passed=recheck_passed,
    )


def _fx(kind: str, arg: str | None = None) -> FsmEffect:
    return FsmEffect(kind=kind, arg=arg)


def _effects_equal(actual: list[FsmEffect], expected: list[FsmEffect]) -> bool:
    return [(e.kind, e.arg) for e in actual] == [(e.kind, e.arg) for e in expected]


@pytest.fixture
def fsm() -> DealFsmService:
    return DealFsmService()


# --- А: строки таблицы ---


def test_a_opportunity_take_require_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(require_ack_open=True), _ev("take"), _NOW
    )
    assert r.new_state == "awaiting_open_ack"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("notify", "ack_open")])
    assert r.duplicate is False


def test_a_opportunity_take_no_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(_ctx(require_ack_open=False), _ev("take"), _NOW)
    assert r.new_state == "buy_order"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("create_order", "buy")])


def test_a_ack_open_recheck_true(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_open_ack"),
        _ev("ack_open", recheck_passed=True),
        _NOW,
    )
    assert r.new_state == "buy_order"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("create_order", "buy")])


def test_a_ack_open_recheck_false(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_open_ack"),
        _ev("ack_open", recheck_passed=False),
        _NOW,
    )
    assert r.new_state == "cancelled"
    assert r.new_row_version == 2
    assert _effects_equal(
        r.effects,
        [_fx("notify", "recheck_failed"), _fx("audit", "recheck_failed")],
    )


def test_a_ack_open_recheck_none(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(state="awaiting_open_ack"),
            _ev("ack_open", recheck_passed=None),
            _NOW,
        )


def test_a_awaiting_open_ack_reject(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_open_ack"), _ev("reject"), _NOW
    )
    assert r.new_state == "cancelled"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("audit", "operator_reject")])


def test_a_awaiting_open_ack_timeout(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_open_ack", state_deadline_at=_DEADLINE_PAST),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "cancelled"
    assert _effects_equal(r.effects, [_fx("notify", "open_timeout")])


def test_a_buy_payment_require_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="buy_order", require_ack_pay=True, has_receipt_out=True),
        _ev("payment_out_ready"),
        _NOW,
    )
    assert r.new_state == "awaiting_pay_ack"
    assert _effects_equal(r.effects, [_fx("notify", "ack_pay")])


def test_a_buy_payment_no_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="buy_order", require_ack_pay=False, has_receipt_out=True),
        _ev("payment_out_ready"),
        _NOW,
    )
    assert r.new_state == "mark_paid"
    assert _effects_equal(r.effects, [_fx("mark_paid")])


def test_a_buy_timeout(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="buy_order", state_deadline_at=_DEADLINE_PAST),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "cancelled"
    assert _effects_equal(
        r.effects,
        [_fx("cancel_order", "buy"), _fx("notify", "buy_timeout")],
    )


def test_a_ack_pay(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_pay_ack", has_receipt_out=True),
        _ev("ack_pay"),
        _NOW,
    )
    assert r.new_state == "mark_paid"
    assert _effects_equal(r.effects, [_fx("mark_paid")])


def test_a_awaiting_pay_reject(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_pay_ack"), _ev("reject"), _NOW
    )
    assert r.new_state == "buy_order"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("audit", "operator_reject")])


def test_a_awaiting_pay_timeout_same_state(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_pay_ack", state_deadline_at=_DEADLINE_PAST),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "awaiting_pay_ack"
    assert r.new_row_version == 1
    assert _effects_equal(r.effects, [_fx("remind", "ack_pay")])


def test_a_mark_paid_confirmed(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="mark_paid"), _ev("mark_paid_confirmed"), _NOW
    )
    assert r.new_state == "awaiting_crypto"
    assert r.effects == []


def test_a_crypto_received(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_crypto"), _ev("crypto_received"), _NOW
    )
    assert r.new_state == "sell_order"
    assert _effects_equal(r.effects, [_fx("create_order", "sell")])


def test_a_awaiting_crypto_timeout(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_crypto", state_deadline_at=_DEADLINE_PAST),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "awaiting_crypto"
    assert r.new_row_version == 1
    assert _effects_equal(r.effects, [_fx("remind", "crypto")])


def test_a_sell_order_created(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="sell_order"), _ev("sell_order_created"), _NOW
    )
    assert r.new_state == "awaiting_incoming"
    assert _effects_equal(r.effects, [_fx("notify", "sell_order_created")])


def test_a_payment_matched_require_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(
            state="awaiting_incoming",
            require_ack_release=True,
            has_receipt_in=True,
        ),
        _ev("payment_matched"),
        _NOW,
    )
    assert r.new_state == "awaiting_release_ack"
    assert _effects_equal(r.effects, [_fx("notify", "ack_release")])


def test_a_payment_matched_no_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(
            state="awaiting_incoming",
            require_ack_release=False,
            has_receipt_in=True,
        ),
        _ev("payment_matched"),
        _NOW,
    )
    assert r.new_state == "released"
    assert _effects_equal(r.effects, [_fx("release")])


def test_a_ack_release_ok(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(
            state="awaiting_release_ack",
            has_receipt_in=True,
            payment_matched=True,
        ),
        _ev("ack_release"),
        _NOW,
    )
    assert r.new_state == "released"
    assert _effects_equal(r.effects, [_fx("release")])


def test_a_awaiting_release_reject(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_release_ack"), _ev("reject"), _NOW
    )
    assert r.new_state == "awaiting_release_ack"
    assert r.new_row_version == 1
    assert _effects_equal(r.effects, [_fx("notify", "release_rejected")])


def test_a_awaiting_release_timeout(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(
            state="awaiting_release_ack", state_deadline_at=_DEADLINE_PAST
        ),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "awaiting_release_ack"
    assert r.new_row_version == 1
    assert _effects_equal(r.effects, [_fx("remind", "ack_release")])


def test_a_release_confirmed(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="released"), _ev("release_confirmed"), _NOW
    )
    assert r.new_state == "closed"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("record_pnl")])


def test_a_dispute_opened_from_buy(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="buy_order"), _ev("dispute_opened"), _NOW
    )
    assert r.new_state == "dispute"
    assert _effects_equal(
        r.effects,
        [_fx("notify", "dispute"), _fx("audit", "dispute_opened")],
    )


# --- Б: недопустимые пары ---


def _invalid_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for state in _STATES:
        for event in _EVENTS:
            if (state, event) not in _ALLOWED_PAIRS:
                pairs.append((state, event))
    return pairs


@pytest.mark.parametrize("state,event", _invalid_pairs())
def test_b_invalid_pair(
    fsm: DealFsmService, state: str, event: str
) -> None:
    ctx = _ctx(
        state=state,
        state_deadline_at=_DEADLINE_PAST if event == "timeout" else None,
        has_receipt_out=True,
        has_receipt_in=True,
        payment_matched=True,
    )
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            ctx,
            _ev(
                event,
                recheck_passed=True if event == "ack_open" else None,
            ),
            _NOW,
        )


# --- В: ReceiptRequired ---


def test_v_payment_out_without_receipt(fsm: DealFsmService) -> None:
    with pytest.raises(ReceiptRequired):
        fsm.transition(
            _ctx(state="buy_order", has_receipt_out=False),
            _ev("payment_out_ready"),
            _NOW,
        )


def test_v_ack_pay_without_receipt(fsm: DealFsmService) -> None:
    with pytest.raises(ReceiptRequired):
        fsm.transition(
            _ctx(state="awaiting_pay_ack", has_receipt_out=False),
            _ev("ack_pay"),
            _NOW,
        )


def test_v_payment_matched_without_receipt(fsm: DealFsmService) -> None:
    with pytest.raises(ReceiptRequired):
        fsm.transition(
            _ctx(state="awaiting_incoming", has_receipt_in=False),
            _ev("payment_matched"),
            _NOW,
        )


def test_v_ack_release_without_receipt(fsm: DealFsmService) -> None:
    with pytest.raises(ReceiptRequired):
        fsm.transition(
            _ctx(
                state="awaiting_release_ack",
                has_receipt_in=False,
                payment_matched=True,
            ),
            _ev("ack_release"),
            _NOW,
        )


def test_v_ack_release_without_payment_matched(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(
                state="awaiting_release_ack",
                has_receipt_in=True,
                payment_matched=False,
            ),
            _ev("ack_release"),
            _NOW,
        )


# --- Г: duplicate event_id ---


def test_g_duplicate_ignores_row_version(fsm: DealFsmService) -> None:
    ctx = _ctx(state="buy_order", processed_event_ids=frozenset({"dup"}))
    r = fsm.transition(
        ctx, _ev("payment_out_ready", event_id="dup", row_version=99), _NOW
    )
    assert r.duplicate is True
    assert r.new_state == "buy_order"
    assert r.new_row_version == 1
    assert r.effects == []


def test_g_duplicate_after_new_service_instance() -> None:
    ctx = _ctx(
        state="opportunity", processed_event_ids=frozenset({"same"})
    )
    a = DealFsmService().transition(ctx, _ev("take", event_id="same"), _NOW)
    b = DealFsmService().transition(ctx, _ev("take", event_id="same"), _NOW)
    assert a.duplicate is True and b.duplicate is True
    assert a.new_state == b.new_state == "opportunity"
    assert a.effects == b.effects == []


# --- Д: row_version ---


def test_d_row_version_mismatch(fsm: DealFsmService) -> None:
    with pytest.raises(ConcurrentModificationError):
        fsm.transition(
            _ctx(state="opportunity", row_version=1),
            _ev("take", row_version=2),
            _NOW,
        )


def test_d_row_version_bumps_only_on_state_change(fsm: DealFsmService) -> None:
    changed = fsm.transition(_ctx(state="opportunity"), _ev("take"), _NOW)
    assert changed.new_state != "opportunity"
    assert changed.new_row_version == 2

    same = fsm.transition(
        _ctx(state="awaiting_pay_ack", state_deadline_at=_DEADLINE_PAST),
        _ev("timeout"),
        _NOW,
    )
    assert same.new_state == "awaiting_pay_ack"
    assert same.new_row_version == 1


# --- Е: kill switch ---


def test_e_kill_ack_open_raises(fsm: DealFsmService) -> None:
    with pytest.raises(KillSwitchError):
        fsm.transition(
            _ctx(state="awaiting_open_ack", kill_switch=True),
            _ev("ack_open", recheck_passed=True),
            _NOW,
        )


def test_e_kill_opportunity_take(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(kill_switch=True), _ev("take"), _NOW
    )
    assert r.new_state == "cancelled"
    assert r.new_row_version == 2
    assert _effects_equal(r.effects, [_fx("audit", "kill_switch")])


def test_e_kill_awaiting_open_reject(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_open_ack", kill_switch=True),
        _ev("reject"),
        _NOW,
    )
    assert r.new_state == "cancelled"
    assert _effects_equal(r.effects, [_fx("audit", "kill_switch")])


def test_e_kill_buy_payment_out_freezes(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="buy_order", kill_switch=True, has_receipt_out=True),
        _ev("payment_out_ready"),
        _NOW,
    )
    assert r.new_state == "buy_order"
    assert r.new_row_version == 1
    assert r.duplicate is False
    assert _effects_equal(
        r.effects, [_fx("alert_operator", "kill_switch")]
    )


def test_e_kill_buy_timeout_cancels(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(
            state="buy_order",
            kill_switch=True,
            state_deadline_at=_DEADLINE_PAST,
        ),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "cancelled"
    assert _effects_equal(
        r.effects,
        [
            _fx("cancel_order", "buy"),
            _fx("notify", "kill_switch"),
            _fx("audit", "kill_switch"),
        ],
    )


@pytest.mark.parametrize(
    "state",
    [
        "awaiting_pay_ack",
        "mark_paid",
        "awaiting_crypto",
        "sell_order",
        "awaiting_incoming",
        "awaiting_release_ack",
        "released",
    ],
)
def test_e_kill_freeze_after_buy(fsm: DealFsmService, state: str) -> None:
    # берём любое событие из таблицы для state
    event_by_state = {
        "awaiting_pay_ack": "ack_pay",
        "mark_paid": "mark_paid_confirmed",
        "awaiting_crypto": "crypto_received",
        "sell_order": "sell_order_created",
        "awaiting_incoming": "payment_matched",
        "awaiting_release_ack": "ack_release",
        "released": "release_confirmed",
    }
    r = fsm.transition(
        _ctx(
            state=state,
            kill_switch=True,
            has_receipt_out=True,
            has_receipt_in=True,
            payment_matched=True,
        ),
        _ev(event_by_state[state]),
        _NOW,
    )
    assert r.new_state == state
    assert r.new_row_version == 1
    assert r.duplicate is False
    assert _effects_equal(
        r.effects, [_fx("alert_operator", "kill_switch")]
    )


def test_e_kill_missing_pair_still_invalid(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(state="buy_order", kill_switch=True),
            _ev("take"),
            _NOW,
        )


def test_e_kill_dispute_opened_follows_table(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="buy_order", kill_switch=True),
        _ev("dispute_opened"),
        _NOW,
    )
    assert r.new_state == "dispute"
    assert _effects_equal(
        r.effects,
        [_fx("notify", "dispute"), _fx("audit", "dispute_opened")],
    )


# --- Ж: timeout ---


def test_zh_timeout_before_deadline(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(
                state="awaiting_open_ack",
                state_deadline_at=_DEADLINE_FUTURE,
            ),
            _ev("timeout"),
            _NOW,
        )


def test_zh_timeout_deadline_none(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(state="awaiting_open_ack", state_deadline_at=None),
            _ev("timeout"),
            _NOW,
        )


def test_zh_timeout_at_exact_deadline(fsm: DealFsmService) -> None:
    deadline = _NOW
    r = fsm.transition(
        _ctx(state="awaiting_open_ack", state_deadline_at=deadline),
        _ev("timeout"),
        _NOW,
    )
    assert r.new_state == "cancelled"


def test_zh_timeout_naive_now(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(
                state="awaiting_open_ack",
                state_deadline_at=_DEADLINE_PAST,
            ),
            _ev("timeout"),
            datetime(2026, 1, 1, 12, 0, 0),
        )


def test_zh_timeout_naive_deadline(fsm: DealFsmService) -> None:
    with pytest.raises(InvalidTransitionError):
        fsm.transition(
            _ctx(
                state="awaiting_open_ack",
                state_deadline_at=datetime(2026, 1, 1, 11, 0, 0),
            ),
            _ev("timeout"),
            _NOW,
        )


# --- З: сквозные сценарии ---


def test_z_happy_path_all_acks(fsm: DealFsmService) -> None:
    steps: list[tuple[str, str, dict[str, Any], str, list[FsmEffect]]] = [
        (
            "opportunity",
            "take",
            {"require_ack_open": True},
            "awaiting_open_ack",
            [_fx("notify", "ack_open")],
        ),
        (
            "awaiting_open_ack",
            "ack_open",
            {"recheck_passed": True},
            "buy_order",
            [_fx("create_order", "buy")],
        ),
        (
            "buy_order",
            "payment_out_ready",
            {"require_ack_pay": True, "has_receipt_out": True},
            "awaiting_pay_ack",
            [_fx("notify", "ack_pay")],
        ),
        (
            "awaiting_pay_ack",
            "ack_pay",
            {"has_receipt_out": True},
            "mark_paid",
            [_fx("mark_paid")],
        ),
        (
            "mark_paid",
            "mark_paid_confirmed",
            {},
            "awaiting_crypto",
            [],
        ),
        (
            "awaiting_crypto",
            "crypto_received",
            {},
            "sell_order",
            [_fx("create_order", "sell")],
        ),
        (
            "sell_order",
            "sell_order_created",
            {},
            "awaiting_incoming",
            [_fx("notify", "sell_order_created")],
        ),
        (
            "awaiting_incoming",
            "payment_matched",
            {"require_ack_release": True, "has_receipt_in": True},
            "awaiting_release_ack",
            [_fx("notify", "ack_release")],
        ),
        (
            "awaiting_release_ack",
            "ack_release",
            {"has_receipt_in": True, "payment_matched": True},
            "released",
            [_fx("release")],
        ),
        (
            "released",
            "release_confirmed",
            {},
            "closed",
            [_fx("record_pnl")],
        ),
    ]
    version = 1
    for state, event, flags, exp_state, exp_fx in steps:
        recheck = flags.pop("recheck_passed", None)
        ctx = _ctx(state=state, row_version=version, **flags)
        r = fsm.transition(
            ctx, _ev(event, row_version=version, recheck_passed=recheck), _NOW
        )
        assert r.new_state == exp_state
        assert _effects_equal(r.effects, exp_fx)
        if exp_state != state:
            assert r.new_row_version == version + 1
            version = r.new_row_version
        else:
            assert r.new_row_version == version


def test_z_happy_path_no_acks(fsm: DealFsmService) -> None:
    version = 1
    seq = [
        (
            "opportunity",
            "take",
            {"require_ack_open": False},
            "buy_order",
            [_fx("create_order", "buy")],
        ),
        (
            "buy_order",
            "payment_out_ready",
            {"require_ack_pay": False, "has_receipt_out": True},
            "mark_paid",
            [_fx("mark_paid")],
        ),
        ("mark_paid", "mark_paid_confirmed", {}, "awaiting_crypto", []),
        (
            "awaiting_crypto",
            "crypto_received",
            {},
            "sell_order",
            [_fx("create_order", "sell")],
        ),
        (
            "sell_order",
            "sell_order_created",
            {},
            "awaiting_incoming",
            [_fx("notify", "sell_order_created")],
        ),
        (
            "awaiting_incoming",
            "payment_matched",
            {"require_ack_release": False, "has_receipt_in": True},
            "released",
            [_fx("release")],
        ),
        (
            "released",
            "release_confirmed",
            {},
            "closed",
            [_fx("record_pnl")],
        ),
    ]
    for state, event, flags, exp_state, exp_fx in seq:
        ctx = _ctx(state=state, row_version=version, **flags)
        r = fsm.transition(ctx, _ev(event, row_version=version), _NOW)
        assert r.new_state == exp_state
        assert _effects_equal(r.effects, exp_fx)
        version = r.new_row_version


def test_z_cancel_in_awaiting_open_ack(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_open_ack"), _ev("reject"), _NOW
    )
    assert r.new_state == "cancelled"
    assert _effects_equal(r.effects, [_fx("audit", "operator_reject")])


def test_z_reject_pay_back_to_buy(fsm: DealFsmService) -> None:
    r = fsm.transition(
        _ctx(state="awaiting_pay_ack"), _ev("reject"), _NOW
    )
    assert r.new_state == "buy_order"
    assert _effects_equal(r.effects, [_fx("audit", "operator_reject")])


# --- И: провайдер ---


@pytest.mark.asyncio
async def test_i_provider_resolves() -> None:
    container = make_async_container(DealFsmServiceProvider())
    async with container() as request_container:
        resolved: Any = await request_container.get(DealFsmService)
        assert isinstance(resolved, DealFsmService)
    await container.close()
