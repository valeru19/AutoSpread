"""Частичный индекс открытых сделок используется планировщиком."""

from __future__ import annotations

from sqlalchemy import text


def test_open_deals_index_used(db, seed_market):
    # На крошечной таблице seqscan дешевле — отключаем, чтобы проверить индекс.
    db.execute(text("SET LOCAL enable_seqscan = off"))
    plan = db.execute(
        text(
            "EXPLAIN (FORMAT TEXT) "
            "SELECT id FROM deal WHERE state NOT IN ('closed', 'cancelled')"
        )
    ).fetchall()
    plan_text = "\n".join(row[0] for row in plan)
    assert "ix_deal_open_states" in plan_text
