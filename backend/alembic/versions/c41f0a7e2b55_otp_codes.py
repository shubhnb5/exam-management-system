"""OTP codes table and verified-mobile timestamp on student accounts

Revision ID: c41f0a7e2b55
Revises: b7c41e2d9a10
Create Date: 2026-11-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41f0a7e2b55'
down_revision: Union[str, None] = 'b7c41e2d9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mobile_number', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("purpose IN ('signup', 'reset')", name='ck_otp_codes_purpose'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_otp_codes_mobile_purpose_created', 'otp_codes', ['mobile_number', 'purpose', 'created_at'])
    op.add_column('student_accounts', sa.Column('mobile_verified_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('student_accounts', 'mobile_verified_at')
    op.drop_index('ix_otp_codes_mobile_purpose_created', table_name='otp_codes')
    op.drop_table('otp_codes')
