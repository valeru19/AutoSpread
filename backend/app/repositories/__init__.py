"""Репозитории домена."""

from app.repositories.ad_snapshot_repository import (
    AdSnapshotRepository,
    ad_snapshot_repository,
)
from app.repositories.agent_proposal_repository import (
    AgentProposalRepository,
    agent_proposal_repository,
)
from app.repositories.audit_event_repository import (
    AuditEventRepository,
    audit_event_repository,
)
from app.repositories.balance_snapshot_repository import (
    BalanceSnapshotRepository,
    balance_snapshot_repository,
)
from app.repositories.chat_message_repository import (
    ChatMessageRepository,
    chat_message_repository,
)
from app.repositories.config_version_repository import (
    ConfigVersionRepository,
    config_version_repository,
)
from app.repositories.counterparty_repository import (
    CounterpartyRepository,
    counterparty_repository,
)
from app.repositories.deal_repository import DealRepository, deal_repository
from app.repositories.exchange_account_repository import (
    ExchangeAccountRepository,
    exchange_account_repository,
)
from app.repositories.exchange_call_repository import (
    ExchangeCallRepository,
    exchange_call_repository,
)
from app.repositories.ledger_entry_repository import (
    LedgerEntryRepository,
    ledger_entry_repository,
)
from app.repositories.operator_action_repository import (
    OperatorActionRepository,
    operator_action_repository,
)
from app.repositories.opportunity_repository import (
    OpportunityRepository,
    opportunity_repository,
)
from app.repositories.order_leg_repository import (
    OrderLegRepository,
    order_leg_repository,
)
from app.repositories.payment_instrument_repository import (
    PaymentInstrumentRepository,
    payment_instrument_repository,
)
from app.repositories.payment_repository import PaymentRepository, payment_repository
from app.repositories.receipt_repository import ReceiptRepository, receipt_repository

__all__ = [
    "AdSnapshotRepository",
    "AgentProposalRepository",
    "AuditEventRepository",
    "BalanceSnapshotRepository",
    "ChatMessageRepository",
    "ConfigVersionRepository",
    "CounterpartyRepository",
    "DealRepository",
    "ExchangeAccountRepository",
    "ExchangeCallRepository",
    "LedgerEntryRepository",
    "OperatorActionRepository",
    "OpportunityRepository",
    "OrderLegRepository",
    "PaymentInstrumentRepository",
    "PaymentRepository",
    "ReceiptRepository",
    "ad_snapshot_repository",
    "agent_proposal_repository",
    "audit_event_repository",
    "balance_snapshot_repository",
    "chat_message_repository",
    "config_version_repository",
    "counterparty_repository",
    "deal_repository",
    "exchange_account_repository",
    "exchange_call_repository",
    "ledger_entry_repository",
    "operator_action_repository",
    "opportunity_repository",
    "order_leg_repository",
    "payment_instrument_repository",
    "payment_repository",
    "receipt_repository",
]
