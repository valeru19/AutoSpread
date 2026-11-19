"""Фикстуры: отдельная БД autospread_test, миграции, sync-сессия с откатом."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from importlib import reload

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# До любых импортов app.core.config: тесты только на autospread_test.
_raw = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://autospread:autospread@127.0.0.1:5433/autospread",
)
_sync = _raw.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
if _sync.rstrip("/").endswith("/autospread"):
    TEST_DB_URL = _sync.rstrip("/") + "_test"
else:
    TEST_DB_URL = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://autospread:autospread@127.0.0.1:5433/autospread_test",
    )

os.environ["DATABASE_URL"] = TEST_DB_URL.replace(
    "postgresql+psycopg://", "postgresql+asyncpg://", 1
)

ADMIN_URL = TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"


def _ensure_test_database() -> None:
    engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'autospread_test'")
        ).scalar()
        if not exists:
            conn.execute(text("CREATE DATABASE autospread_test OWNER autospread"))
    engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _ensure_test_database()
    import app.core.config as config_mod

    reload(config_mod)

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    eng = create_engine(TEST_DB_URL, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Каждый тест в транзакции с ROLLBACK — изоляция без TRUNCATE."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def seed_market(db: Session):
    """Минимальный граф: account, counterparty, 2 ad_snapshot, config, opportunity, deal."""
    from app.models import (
        AdSnapshot,
        ConfigVersion,
        Counterparty,
        Deal,
        ExchangeAccount,
        Opportunity,
    )

    account = ExchangeAccount(
        exchange="bybit",
        label="test-main",
        secret_ref="BYBIT_API_KEY",
        permissions={"trade": True, "withdraw": False},
        mode="paper",
    )
    cp = Counterparty(exchange="bybit", external_id="cp-1", nickname="seller1")
    cfg = ConfigVersion(version=1, params={"require_ack": True}, created_by=1, comment="test")
    db.add_all([account, cp, cfg])
    db.flush()

    now = datetime.now(UTC)
    buy_ad = AdSnapshot(
        exchange="bybit",
        external_ad_id="ad-buy-1",
        token="USDT",
        currency="KZT",
        side="buy",
        price=Decimal("500.12345678"),
        available_amount=Decimal("1000.123456789012345678"),
        min_amount=Decimal("1000.0000"),
        max_amount=Decimal("500000.0000"),
        payment_methods=["kaspi"],
        counterparty_id=cp.id,
        captured_at=now,
        raw={},
    )
    sell_ad = AdSnapshot(
        exchange="bybit",
        external_ad_id="ad-sell-1",
        token="USDT",
        currency="KZT",
        side="sell",
        price=Decimal("510.12345678"),
        available_amount=Decimal("800.000000000000000000"),
        min_amount=Decimal("1000.0000"),
        max_amount=Decimal("400000.0000"),
        payment_methods=["kaspi"],
        counterparty_id=cp.id,
        captured_at=now,
        raw={},
    )
    db.add_all([buy_ad, sell_ad])
    db.flush()

    opp = Opportunity(
        currency="KZT",
        buy_ad_snapshot_id=buy_ad.id,
        sell_ad_snapshot_id=sell_ad.id,
        amount_token=Decimal("100.000000000000000000"),
        buy_price=buy_ad.price,
        sell_price=sell_ad.price,
        gross_margin_pct=Decimal("2.000000"),
        net_margin_pct=Decimal("1.500000"),
        net_profit_fiat=Decimal("1500.0000"),
        fees={},
        calc_inputs={},
        config_version_id=cfg.id,
        decision="taken",
    )
    db.add(opp)
    db.flush()

    deal = Deal(
        opportunity_id=opp.id,
        currency="KZT",
        state="buy_order",
        mode="paper",
        amount_token=opp.amount_token,
        planned_margin_pct=opp.net_margin_pct,
        planned_profit_fiat=opp.net_profit_fiat,
        config_version_id=cfg.id,
    )
    db.add(deal)
    db.flush()

    return {
        "account": account,
        "counterparty": cp,
        "config": cfg,
        "buy_ad": buy_ad,
        "sell_ad": sell_ad,
        "opportunity": opp,
        "deal": deal,
    }
