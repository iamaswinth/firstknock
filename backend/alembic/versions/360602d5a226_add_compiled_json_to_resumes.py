"""add compiled_json to resumes

Revision ID: 360602d5a226
Revises: 003
Create Date: 2026-06-06 16:03:23.025258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '360602d5a226'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resumes', sa.Column('compiled_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('resumes', 'compiled_json')
