"""CHECK, UNIQUE, FK RESTRICT."""

from __future__ import annotations

from decimal import Decimal
from datetime import UTC, datetime
import uuid

import pytest
from sqlalchemy.exc import IntegrityError


def test_invalid_currency_rejected(db, seed_market):
    from app.models import Deal

    deal = seed_market["deal"]
    deal.currency = "BTC"
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_invalid_deal_state_rejected(db, seed_market):
    from app.models import Deal

    deal = seed_market["deal"]
    deal.state = "flying"
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_ledger_amount_must_be_positive(db, seed_market):
    from app.models import LedgerEntry

    row = LedgerEntry(
        transaction_id=uuid.uuid4(),
        debit_account="bybit:usdt",
        credit_account="pnl",
        amount=Decimal("0"),
        asset="USDT",
        deal_id=seed_market["deal"].id,
    )
    db.add(row)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_permissions_withdraw_true_rejected(db):
    from app.models import ExchangeAccount

    acc = ExchangeAccount(
        exchange="bybit",
        label="bad-withdraw",
        secret_ref="X",
        permissions={"withdraw": True},
        mode="paper",
    )
    db.add(acc)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_unique_idempotency_key(db, seed_market):
    from app.models import OrderLeg

    m = seed_market
    a = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="buy",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("500"),
        amount_fiat=Decimal("5000"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["buy_ad"].id,
        idempotency_key="idem-1",
    )
    b = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="sell",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("510"),
        amount_fiat=Decimal("5100"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["sell_ad"].id,
        idempotency_key="idem-1",
    )
    db.add(a)
    db.flush()
    db.add(b)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_unique_deal_side(db, seed_market):
    from app.models import OrderLeg

    m = seed_market
    a = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="buy",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("500"),
        amount_fiat=Decimal("5000"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["buy_ad"].id,
        idempotency_key="idem-a",
    )
    b = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="buy",
        currency="KZT",
        amount_token=Decimal("11"),
        price=Decimal("501"),
        amount_fiat=Decimal("5511"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["buy_ad"].id,
        idempotency_key="idem-b",
    )
    db.add(a)
    db.flush()
    db.add(b)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_unique_counterparty_exchange_external(db):
    from app.models import Counterparty

    db.add(Counterparty(exchange="bybit", external_id="dup"))
    db.flush()
    db.add(Counterparty(exchange="bybit", external_id="dup"))
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_partial_unique_external_order_id(db, seed_market):
    from app.models import OrderLeg

    m = seed_market
    a = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="buy",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("500"),
        amount_fiat=Decimal("5000"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["buy_ad"].id,
        idempotency_key="idem-ext-a",
        external_order_id="EXT-1",
    )
    b = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="sell",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("510"),
        amount_fiat=Decimal("5100"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["sell_ad"].id,
        idempotency_key="idem-ext-b",
        external_order_id="EXT-1",
    )
    db.add(a)
    db.flush()
    db.add(b)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()


def test_fk_restrict_delete_parent(db, seed_market):
    from app.models import Counterparty
    from sqlalchemy import delete

    cp_id = seed_market["counterparty"].id
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(delete(Counterparty).where(Counterparty.id == cp_id))
            db.flush()


def test_composite_fk_currency_mismatch(db, seed_market):
    """C1: order_leg.currency должен совпадать с deal.currency."""
    from app.models import OrderLeg

    m = seed_market
    leg = OrderLeg(
        deal_id=m["deal"].id,
        exchange_account_id=m["account"].id,
        side="buy",
        currency="RUB",  # deal в KZT
        amount_token=Decimal("10"),
        price=Decimal("500"),
        amount_fiat=Decimal("5000"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["buy_ad"].id,
        idempotency_key="idem-c1",
    )
    db.add(leg)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.flush()
