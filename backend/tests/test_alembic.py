"""Миграции: upgrade/downgrade и сверка с metadata."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


def test_upgrade_downgrade_upgrade(engine):
    """Цикл head → base → head на тестовой БД; в конце снова head для остальных тестов."""
    cfg = Config("alembic.ini")
    try:
        command.downgrade(cfg, "base")
        insp = inspect(engine)
        assert "deal" not in insp.get_table_names()

        command.upgrade(cfg, "head")
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        expected = {
            "exchange_account",
            "counterparty",
            "ad_snapshot",
            "config_version",
            "opportunity",
            "payment_instrument",
            "deal",
            "order_leg",
            "payment",
            "receipt",
            "chat_message",
            "operator_action",
            "balance_snapshot",
            "ledger_entry",
            "audit_event",
            "agent_proposal",
            "exchange_call",
        }
        assert expected.issubset(tables)

        with engine.connect() as conn:
            triggers = conn.execute(
                text(
                    "SELECT count(*) FROM pg_trigger "
                    "WHERE tgname LIKE 'trg_%_forbid_mutation'"
                )
            ).scalar()
        assert triggers == 7
    finally:
        command.upgrade(cfg, "head")


def test_alembic_check_no_diff(engine):
    """Модели и БД после upgrade совпадают (alembic check)."""
    cfg = Config("alembic.ini")
    command.check(cfg)


def test_revision_chain():
    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    assert len(script.get_heads()) == 1
