"""District of an exam center (printed on admit cards)

Revision ID: d5e8a1c3f7b2
Revises: c41f0a7e2b55
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e8a1c3f7b2'
down_revision: Union[str, None] = 'c41f0a7e2b55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('exam_centers', sa.Column('district', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('exam_centers', 'district')
