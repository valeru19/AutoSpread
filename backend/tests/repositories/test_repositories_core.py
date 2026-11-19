"""Репозитории: create, спец-выборки, append-only API, integrity."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_exceptions import AppendOnlyViolation
from app.repositories import (
    ad_snapshot_repository,
    config_version_repository,
    counterparty_repository,
    deal_repository,
    exchange_account_repository,
    exchange_call_repository,
    order_leg_repository,
)


@pytest.mark.asyncio
async def test_config_get_active(async_db: AsyncSession) -> None:
    await config_version_repository.create(
        async_db, version=100, params={}, created_by=1
    )
    await config_version_repository.create(
        async_db, version=101, params={"x": 1}, created_by=1
    )
    active = await config_version_repository.get_active(async_db)
    assert active is not None
    assert active.version == 101


@pytest.mark.asyncio
async def test_ad_snapshot_list_latest_and_append_only(
    async_db: AsyncSession, market_ids: dict[str, int]
) -> None:
    rows = await ad_snapshot_repository.list_latest(
        async_db, "KZT", "sell", limit=10
    )
    assert len(rows) >= 1
    assert rows[0].currency == "KZT"

    with pytest.raises(AppendOnlyViolation):
        await ad_snapshot_repository.update(
            async_db, market_ids["buy_ad_id"], external_ad_id="x"
        )
    with pytest.raises(AppendOnlyViolation):
        await ad_snapshot_repository.delete(async_db, market_ids["buy_ad_id"])


@pytest.mark.asyncio
async def test_deal_list_open(
    async_db: AsyncSession, market_ids: dict[str, int]
) -> None:
    open_deals = await deal_repository.list_open(async_db)
    assert any(d.id == market_ids["deal_id"] for d in open_deals)

    await deal_repository.update(
        async_db, market_ids["deal_id"], state="closed"
    )
    open_deals2 = await deal_repository.list_open(async_db)
    assert all(d.id != market_ids["deal_id"] for d in open_deals2)


@pytest.mark.asyncio
async def test_counterparty_unique_integrity(async_db: AsyncSession) -> None:
    await counterparty_repository.create(
        async_db, exchange="bybit", external_id="dup-x"
    )
    with pytest.raises(IntegrityError):
        async with async_db.begin_nested():
            await counterparty_repository.create(
                async_db, exchange="bybit", external_id="dup-x"
            )


@pytest.mark.asyncio
async def test_exchange_account_withdraw_check(async_db: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        async with async_db.begin_nested():
            await exchange_account_repository.create(
                async_db,
                exchange="bybit",
                label="bad",
                secret_ref="X",
                permissions={"withdraw": True},
                mode="paper",
            )


@pytest.mark.asyncio
async def test_composite_fk_currency_mismatch(
    async_db: AsyncSession, market_ids: dict[str, int]
) -> None:
    with pytest.raises(IntegrityError):
        async with async_db.begin_nested():
            await order_leg_repository.create(
                async_db,
                deal_id=market_ids["deal_id"],
                exchange_account_id=market_ids["account_id"],
                side="buy",
                currency="RUB",
                amount_token=Decimal("1"),
                price=Decimal("1"),
                amount_fiat=Decimal("1"),
                status="created",
                counterparty_id=market_ids["counterparty_id"],
                ad_snapshot_id=market_ids["buy_ad_id"],
                idempotency_key="fk-mismatch",
            )


@pytest.mark.asyncio
async def test_order_leg_and_exchange_call(
    async_db: AsyncSession, market_ids: dict[str, int]
) -> None:
    leg = await order_leg_repository.create(
        async_db,
        deal_id=market_ids["deal_id"],
        exchange_account_id=market_ids["account_id"],
        side="buy",
        currency="KZT",
        amount_token=Decimal("10"),
        price=Decimal("500"),
        amount_fiat=Decimal("5000"),
        status="created",
        counterparty_id=market_ids["counterparty_id"],
        ad_snapshot_id=market_ids["buy_ad_id"],
        idempotency_key="leg-ok-1",
    )
    legs = await order_leg_repository.list_by_deal(async_db, market_ids["deal_id"])
    assert len(legs) == 1

    call = await exchange_call_repository.create(
        async_db,
        exchange_account_id=market_ids["account_id"],
        deal_id=market_ids["deal_id"],
        order_leg_id=leg.id,
        operation="create_order",
        idempotency_key="call-1",
        status="started",
        request={},
    )
    unfinished = await exchange_call_repository.list_unfinished(async_db)
    assert any(c.id == call.id for c in unfinished)

    await exchange_call_repository.update(
        async_db, call.id, status="succeeded", finished_at=datetime.now(UTC)
    )
    unfinished2 = await exchange_call_repository.list_unfinished(async_db)
    assert all(c.id != call.id for c in unfinished2)
