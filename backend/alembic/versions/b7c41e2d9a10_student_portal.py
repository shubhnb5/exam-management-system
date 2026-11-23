"""student portal accounts, admit card refresh tracking, normalized mobiles

Revision ID: b7c41e2d9a10
Revises: 5afe184335ba
Create Date: 2026-11-20 12:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c41e2d9a10'
down_revision: Union[str, None] = '5afe184335ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_mobile(raw: str) -> str | None:
    # Frozen copy of app.validators.normalize_mobile (migrations must not
    # depend on application code that may change later).
    text = (raw or "").strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]
    digits = re.sub(r"\D", "", text)
    if len(digits) == 13 and digits.startswith("091"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return None


def upgrade() -> None:
    op.create_table(
        'student_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('middle_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('mobile_number', sa.String(), nullable=False),
        sa.Column('gender', sa.String(), nullable=False),
        sa.Column('aadhaar_encrypted', sa.Text(), nullable=True),
        sa.Column('aadhaar_hash', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("gender IN ('male', 'female', 'other')", name='ck_student_accounts_gender'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('mobile_number'),
        sa.UniqueConstraint('aadhaar_hash'),
    )

    op.add_column('hall_tickets', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    # Uploaded mobile numbers are now stored as plain 10 digits so they can be
    # matched against student logins. Normalize what's already there; values
    # that aren't a recognizable Indian mobile number are left untouched.
    # (Digits-only normalization doesn't change the Roll No printed on tickets,
    # which is derived from the last 7 digits.)
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, mobile_number FROM students")).fetchall()
    for student_id, mobile in rows:
        normalized = _normalize_mobile(mobile)
        if normalized and normalized != mobile:
            conn.execute(
                sa.text("UPDATE students SET mobile_number = :m WHERE id = :id"),
                {"m": normalized, "id": student_id},
            )

    op.create_index('ix_students_mobile_number', 'students', ['mobile_number'])


def downgrade() -> None:
    op.drop_index('ix_students_mobile_number', table_name='students')
    op.drop_column('hall_tickets', 'updated_at')
    op.drop_table('student_accounts')
