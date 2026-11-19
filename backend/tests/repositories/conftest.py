"""Async-сессия для тестов репозиториев (родительский conftest даёт autospread_test)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.conftest import TEST_DB_URL


@pytest.fixture
async def async_db() -> AsyncIterator[AsyncSession]:
    """Транзакция с ROLLBACK на asyncpg."""
    async_url = TEST_DB_URL.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url, pool_pre_ping=True)
    async with engine.connect() as conn:
        trans = await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        session = factory()
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def market_ids(async_db: AsyncSession) -> dict[str, int]:
    """Минимальный граф для сделок: account, cp, config, 2 ads, opportunity, deal."""
    from app.repositories import (
        ad_snapshot_repository,
        config_version_repository,
        counterparty_repository,
        deal_repository,
        exchange_account_repository,
        opportunity_repository,
    )

    account = await exchange_account_repository.create(
        async_db,
        exchange="bybit",
        label="repo-test",
        secret_ref="BYBIT_API_KEY",
        permissions={"trade": True, "withdraw": False},
        mode="paper",
    )
    cp = await counterparty_repository.create(
        async_db,
        exchange="bybit",
        external_id="repo-cp-1",
        nickname="n1",
    )
    cfg = await config_version_repository.create(
        async_db,
        version=9001,
        params={"require_ack": True},
        created_by=1,
        comment="repo-test",
    )
    now = datetime.now(UTC)
    buy = await ad_snapshot_repository.create(
        async_db,
        exchange="bybit",
        external_ad_id="buy-1",
        token="USDT",
        currency="KZT",
        side="sell",  # рекламодатель продаёт → мы покупаем
        price=Decimal("500.00000000"),
        available_amount=Decimal("1000"),
        min_amount=Decimal("1000.0000"),
        max_amount=Decimal("500000.0000"),
        payment_methods=["kaspi"],
        counterparty_id=cp.id,
        captured_at=now,
        raw={},
    )
    sell = await ad_snapshot_repository.create(
        async_db,
        exchange="bybit",
        external_ad_id="sell-1",
        token="USDT",
        currency="KZT",
        side="buy",  # рекламодатель покупает → мы продаём
        price=Decimal("510.00000000"),
        available_amount=Decimal("800"),
        min_amount=Decimal("1000.0000"),
        max_amount=Decimal("400000.0000"),
        payment_methods=["kaspi"],
        counterparty_id=cp.id,
        captured_at=now,
        raw={},
    )
    opp = await opportunity_repository.create(
        async_db,
        currency="KZT",
        buy_ad_snapshot_id=buy.id,
        sell_ad_snapshot_id=sell.id,
        amount_token=Decimal("100"),
        buy_price=buy.price,
        sell_price=sell.price,
        gross_margin_pct=Decimal("2.000000"),
        net_margin_pct=Decimal("1.500000"),
        net_profit_fiat=Decimal("1500.0000"),
        fees={},
        calc_inputs={},
        config_version_id=cfg.id,
        decision="taken",
    )
    deal = await deal_repository.create(
        async_db,
        opportunity_id=opp.id,
        currency="KZT",
        state="buy_order",
        mode="paper",
        amount_token=opp.amount_token,
        planned_margin_pct=opp.net_margin_pct,
        planned_profit_fiat=opp.net_profit_fiat,
        config_version_id=cfg.id,
    )
    return {
        "account_id": account.id,
        "counterparty_id": cp.id,
        "config_id": cfg.id,
        "buy_ad_id": buy.id,
        "sell_ad_id": sell.id,
        "opportunity_id": opp.id,
        "deal_id": deal.id,
    }
