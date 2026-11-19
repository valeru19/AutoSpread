"""Триггеры forbid_mutation: UPDATE/DELETE на append-only таблицах."""

from __future__ import annotations

from decimal import Decimal
import uuid

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError


def test_append_only_update_and_delete(db, seed_market):
    from app.models import (
        AdSnapshot,
        AuditEvent,
        ChatMessage,
        ConfigVersion,
        LedgerEntry,
        OperatorAction,
        OrderLeg,
        Payment,
        Receipt,
    )

    cfg = seed_market["config"]
    ad = seed_market["buy_ad"]
    deal = seed_market["deal"]
    m = seed_market

    leg = OrderLeg(
        deal_id=deal.id,
        exchange_account_id=m["account"].id,
        side="buy",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("500"),
        amount_fiat=Decimal("5000"),
        status="created",
        counterparty_id=m["counterparty"].id,
        ad_snapshot_id=m["buy_ad"].id,
        idempotency_key="idem-append-only",
    )
    db.add(leg)
    db.flush()

    payment = Payment(
        deal_id=deal.id,
        order_leg_id=leg.id,
        direction="out",
        currency="KZT",
        amount=Decimal("5000.0000"),
        status="pending",
    )
    db.add(payment)
    db.flush()

    audit = AuditEvent(
        actor_type="system",
        actor_id="test",
        action="ping",
        entity_type="deal",
        entity_id=deal.id,
        input={},
        result={},
    )
    op = OperatorAction(
        deal_id=deal.id,
        step="open",
        action="ack",
        telegram_user_id=1,
        context={},
    )
    ledger = LedgerEntry(
        transaction_id=uuid.uuid4(),
        debit_account="bybit:usdt",
        credit_account="pnl",
        amount=Decimal("1.5"),
        asset="USDT",
        deal_id=deal.id,
        description="test",
    )
    receipt = Receipt(
        deal_id=deal.id,
        payment_id=payment.id,
        side="out",
        storage_key="receipts/test.png",
        mime="image/png",
        size_bytes=100,
        sha256="a" * 64,
        uploaded_by=1,
    )
    chat = ChatMessage(
        order_leg_id=leg.id,
        direction="in",
        message_text="hello",
        sent_at=deal.created_at,
        raw={},
    )
    db.add_all([audit, op, ledger, receipt, chat])
    db.flush()

    cases = [
        (ConfigVersion, cfg.id, {"comment": "hacked"}),
        (AdSnapshot, ad.id, {"external_ad_id": "hacked"}),
        (AuditEvent, audit.id, {"action": "hacked"}),
        (OperatorAction, op.id, {"action": "reject"}),
        (LedgerEntry, ledger.id, {"description": "hacked"}),
        (Receipt, receipt.id, {"mime": "image/jpeg"}),
        (ChatMessage, chat.id, {"message_text": "tampered"}),
    ]

    for model, pk, values in cases:
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(update(model).where(model.id == pk).values(**values))
                db.flush()

        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(delete(model).where(model.id == pk))
                db.flush()
