"""Общие SQLAlchemy-типы денег (без float)."""

from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import mapped_column

# Крипта
CRYPTO_NUMERIC = Numeric(38, 18)
# Фиатные суммы
FIAT_NUMERIC = Numeric(24, 4)
# Цены / курсы
PRICE_NUMERIC = Numeric(24, 8)
# Проценты маржи
PCT_NUMERIC = Numeric(12, 6)


def crypto_col(**kwargs):
    return mapped_column(CRYPTO_NUMERIC, **kwargs)


def fiat_col(**kwargs):
    return mapped_column(FIAT_NUMERIC, **kwargs)


def price_col(**kwargs):
    return mapped_column(PRICE_NUMERIC, **kwargs)


def pct_col(**kwargs):
    return mapped_column(PCT_NUMERIC, **kwargs)


DecimalType = Decimal
