"""Точность NUMERIC: crypto 38,18 и fiat 24,4 без потерь."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select


def test_crypto_and_fiat_precision_roundtrip(db, seed_market):
    from app.models import AdSnapshot, Deal

    crypto = Decimal("123456789012345.123456789012345678")
    fiat = Decimal("999999999999999999.1234")

    # ad_snapshot append-only — только INSERT, без UPDATE
    ad = AdSnapshot(
        exchange="bybit",
        external_ad_id="ad-precision",
        token="USDT",
        currency="KZT",
        side="buy",
        price=Decimal("500.12345678"),
        available_amount=crypto,
        min_amount=fiat,
        max_amount=Decimal("1.0000"),
        payment_methods=[],
        counterparty_id=seed_market["counterparty"].id,
        captured_at=datetime.now(UTC),
        raw={},
    )
    db.add(ad)
    db.flush()
    db.expire_all()
    loaded = db.execute(select(AdSnapshot).where(AdSnapshot.id == ad.id)).scalar_one()
    assert loaded.available_amount == crypto
    assert loaded.min_amount == fiat

    deal = seed_market["deal"]
    deal.planned_profit_fiat = Decimal("1.2345")
    deal.amount_token = Decimal("0.000000000000000001")
    db.flush()
    db.expire_all()
    d2 = db.execute(select(Deal).where(Deal.id == deal.id)).scalar_one()
    assert d2.planned_profit_fiat == Decimal("1.2345")
    assert d2.amount_token == Decimal("0.000000000000000001")
