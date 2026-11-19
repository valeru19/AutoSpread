"""Строковые enum'ы домена. В БД — VARCHAR + CHECK, не Postgres ENUM."""

from enum import StrEnum


class ExchangeCode(StrEnum):
    BYBIT = "bybit"


class RunMode(StrEnum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE_CONFIRM = "live_confirm"
    LIVE = "live"


class FiatCurrency(StrEnum):
    RUB = "RUB"
    EUR = "EUR"
    USD = "USD"
    KZT = "KZT"


class AdSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OpportunityDecision(StrEnum):
    TAKEN = "taken"
    SKIPPED = "skipped"
    EXPIRED = "expired"


class DealState(StrEnum):
    OPPORTUNITY = "opportunity"
    AWAITING_OPEN_ACK = "awaiting_open_ack"
    BUY_ORDER = "buy_order"
    AWAITING_PAY_ACK = "awaiting_pay_ack"
    MARK_PAID = "mark_paid"
    AWAITING_CRYPTO = "awaiting_crypto"
    SELL_ORDER = "sell_order"
    AWAITING_INCOMING = "awaiting_incoming"
    AWAITING_RELEASE_ACK = "awaiting_release_ack"
    RELEASED = "released"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    DISPUTE = "dispute"


class OrderLegStatus(StrEnum):
    CREATED = "created"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    RELEASED = "released"
    CANCELLED = "cancelled"
    APPEALED = "appealed"


class PaymentDirection(StrEnum):
    IN = "in"
    OUT = "out"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    MATCHED = "matched"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReceiptSide(StrEnum):
    OUT = "out"
    IN = "in"


class ChatDirection(StrEnum):
    IN = "in"
    OUT = "out"
    SYSTEM = "system"


class OperatorStep(StrEnum):
    OPEN = "open"
    PAY = "pay"
    MARK_PAID = "mark_paid"
    RELEASE = "release"
    CANCEL = "cancel"
    PAYMENT_MATCHED = "payment_matched"


class OperatorActionType(StrEnum):
    ACK = "ack"
    REJECT = "reject"


class BalanceSource(StrEnum):
    BYBIT = "bybit"
    MANUAL_FIAT = "manual_fiat"


class ActorType(StrEnum):
    SYSTEM = "system"
    OPERATOR = "operator"
    AGENT = "agent"


class AgentRole(StrEnum):
    ANALYST = "analyst"
    ADVISOR = "advisor"
    EXECUTOR = "executor"


class AgentProposalStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ExchangeCallOperation(StrEnum):
    LIST_ADS = "list_ads"
    CREATE_ORDER = "create_order"
    GET_ORDER = "get_order"
    MARK_PAID = "mark_paid"
    RELEASE = "release"
    CANCEL = "cancel"
    GET_BALANCES = "get_balances"
    CHAT_SEND = "chat_send"
    CHAT_LIST = "chat_list"


class ExchangeCallStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class AuditEntityType(StrEnum):
    DEAL = "deal"
    ORDER_LEG = "order_leg"
    PAYMENT = "payment"
    OPPORTUNITY = "opportunity"
    CONFIG_VERSION = "config_version"
    EXCHANGE_CALL = "exchange_call"
    RECEIPT = "receipt"
    OTHER = "other"
