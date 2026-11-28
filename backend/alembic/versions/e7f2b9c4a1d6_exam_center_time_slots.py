"""Custom exam timings per exam center (time slots), chosen per uploaded sheet

Revision ID: e7f2b9c4a1d6
Revises: d5e8a1c3f7b2
Create Date: 2026-11-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f2b9c4a1d6'
down_revision: Union[str, None] = 'd5e8a1c3f7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exam_center_time_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exam_center_id', sa.Integer(), nullable=False),
        sa.Column('reporting', sa.String(), nullable=False),
        sa.Column('last_entry', sa.String(), nullable=False),
        sa.Column('duration', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['exam_center_id'], ['exam_centers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_exam_center_time_slots_exam_center_id', 'exam_center_time_slots', ['exam_center_id'])

    # Existing students and admit cards keep NULL here = the default timing
    # from ticket_template/config.json, exactly as before.
    op.add_column('students', sa.Column('time_slot_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_students_time_slot_id', 'students', 'exam_center_time_slots', ['time_slot_id'], ['id']
    )
    op.add_column('hall_tickets', sa.Column('timing_reporting', sa.String(), nullable=True))
    op.add_column('hall_tickets', sa.Column('timing_last_entry', sa.String(), nullable=True))
    op.add_column('hall_tickets', sa.Column('timing_duration', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('hall_tickets', 'timing_duration')
    op.drop_column('hall_tickets', 'timing_last_entry')
    op.drop_column('hall_tickets', 'timing_reporting')
    op.drop_constraint('fk_students_time_slot_id', 'students', type_='foreignkey')
    op.drop_column('students', 'time_slot_id')
    op.drop_index('ix_exam_center_time_slots_exam_center_id', table_name='exam_center_time_slots')
    op.drop_table('exam_center_time_slots')
