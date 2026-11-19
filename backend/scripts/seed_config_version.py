"""Первая версия конфига: require_ack на шагах + консервативные лимиты.

Запуск из backend/:
  poetry run python -m scripts.seed_config_version
"""

from __future__ import annotations

import sys
from pathlib import Path

# poetry run из backend — пакет app на PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ConfigVersion


DEFAULT_PARAMS = {
    "require_ack": {
        "open": True,
        "pay": True,
        "mark_paid": True,
        "release": True,
        "cancel": True,
    },
    "limits": {
        "max_deal_usdt": 500,
        "max_open_deals": 1,
        "min_net_margin_pct": 0.5,
        "max_slippage_pct": 0.3,
    },
    "ttl": {
        "ads_days": 90,
        "receipts_days": 1825,
        "operator_ack_seconds": 120,
    },
    "mode_default": "paper",
}


def main() -> None:
    url = settings.db.url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    with Session(engine) as session:
        existing = session.execute(
            select(ConfigVersion).where(ConfigVersion.version == 1)
        ).scalar_one_or_none()
        if existing is not None:
            print(f"config_version v1 already exists id={existing.id}")
            return
        row = ConfigVersion(
            version=1,
            params=DEFAULT_PARAMS,
            created_by=0,
            comment="initial seed: require_ack all steps, conservative limits",
        )
        session.add(row)
        session.commit()
        print(f"seeded config_version id={row.id} version=1")


if __name__ == "__main__":
    main()
