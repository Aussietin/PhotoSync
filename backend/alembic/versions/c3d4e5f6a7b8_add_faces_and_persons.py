"""add faces and persons (local face recognition)

Revision ID: c3d4e5f6a7b8
Revises: b1f2c3d4e5a6
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b1f2c3d4e5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'persons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('is_known', sa.Boolean(), nullable=True),
        sa.Column('cover_face_id', sa.Integer(), nullable=True),
        sa.Column('centroid', sa.LargeBinary(), nullable=True),
        sa.Column('face_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_persons_is_known', 'persons', ['is_known'])

    op.create_table(
        'faces',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('photo_id', sa.Integer(), sa.ForeignKey('photos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id', ondelete='SET NULL'), nullable=True),
        sa.Column('embedding', sa.LargeBinary(), nullable=False),
        sa.Column('bbox_x', sa.Integer(), nullable=True),
        sa.Column('bbox_y', sa.Integer(), nullable=True),
        sa.Column('bbox_w', sa.Integer(), nullable=True),
        sa.Column('bbox_h', sa.Integer(), nullable=True),
        sa.Column('det_score', sa.Float(), nullable=True),
        sa.Column('crop_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_faces_photo_id', 'faces', ['photo_id'])
    op.create_index('ix_faces_person_id', 'faces', ['person_id'])


def downgrade() -> None:
    op.drop_index('ix_faces_person_id', table_name='faces')
    op.drop_index('ix_faces_photo_id', table_name='faces')
    op.drop_table('faces')
    op.drop_index('ix_persons_is_known', table_name='persons')
    op.drop_table('persons')
