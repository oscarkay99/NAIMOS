"""audit log ip_address as string

Revision ID: ac2894f041fe
Revises: 0ecb014a06c8
Create Date: 2026-09-14 16:11:34.003882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ac2894f041fe'
down_revision: Union[str, None] = '0ecb014a06c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # request.client.host isn't guaranteed to be a valid IP (e.g. test clients,
    # some proxy configurations) - store as text rather than reject those writes.
    op.alter_column('audit_logs', 'ip_address',
               existing_type=postgresql.INET(),
               type_=sa.String(length=64),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('audit_logs', 'ip_address',
               existing_type=sa.String(length=64),
               type_=postgresql.INET(),
               existing_nullable=True)
