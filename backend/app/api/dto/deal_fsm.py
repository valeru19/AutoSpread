"""DTO чистого DealFsmService (без БД)."""

from datetime import datetime

from pydantic import BaseModel, Field


class FsmContext(BaseModel):
    """Снимок сделки для одного вызова transition."""

    state: str
    row_version: int
    require_ack_open: bool
    require_ack_pay: bool
    require_ack_release: bool
    has_receipt_out: bool
    has_receipt_in: bool
    payment_matched: bool
    kill_switch: bool
    processed_event_ids: frozenset[str] = Field(default_factory=frozenset)
    state_deadline_at: datetime | None = None


class FsmEvent(BaseModel):
    """Входящее событие FSM."""

    name: str
    event_id: str
    row_version: int
    recheck_passed: bool | None = None


class FsmEffect(BaseModel):
    """Побочный эффект перехода (исполняет оркестратор)."""

    kind: str
    arg: str | None = None


class FsmResult(BaseModel):
    """Результат одного вызова transition."""

    new_state: str
    new_row_version: int
    effects: list[FsmEffect]
    duplicate: bool
