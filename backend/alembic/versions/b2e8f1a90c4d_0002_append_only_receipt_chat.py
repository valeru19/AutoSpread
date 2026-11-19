"""0002_append_only_receipt_chat

Чек и переписка — доказательства: UPDATE/DELETE запрещены триггером forbid_mutation.

Revision ID: b2e8f1a90c4d
Revises: ae4cb034c1ae
Create Date: 2026-11-18

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b2e8f1a90c4d"
down_revision: Union[str, Sequence[str], None] = "ae4cb034c1ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("receipt", "chat_message")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_forbid_mutation
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
            """
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_forbid_mutation ON {table};")
