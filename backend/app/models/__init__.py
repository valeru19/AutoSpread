"""Регистрация моделей для Alembic / metadata."""

from app.models.ad_snapshot import AdSnapshot
from app.models.agent_proposal import AgentProposal
from app.models.audit_event import AuditEvent
from app.models.balance_snapshot import BalanceSnapshot
from app.models.chat_message import ChatMessage
from app.models.config_version import ConfigVersion
from app.models.counterparty import Counterparty
from app.models.deal import Deal
from app.models.exchange_account import ExchangeAccount
from app.models.exchange_call import ExchangeCall
from app.models.ledger_entry import LedgerEntry
from app.models.operator_action import OperatorAction
from app.models.opportunity import Opportunity
from app.models.order_leg import OrderLeg
from app.models.payment import Payment
from app.models.payment_instrument import PaymentInstrument
from app.models.receipt import Receipt

__all__ = [
    "AdSnapshot",
    "AgentProposal",
    "AuditEvent",
    "BalanceSnapshot",
    "ChatMessage",
    "ConfigVersion",
    "Counterparty",
    "Deal",
    "ExchangeAccount",
    "ExchangeCall",
    "LedgerEntry",
    "OperatorAction",
    "Opportunity",
    "OrderLeg",
    "Payment",
    "PaymentInstrument",
    "Receipt",
]
