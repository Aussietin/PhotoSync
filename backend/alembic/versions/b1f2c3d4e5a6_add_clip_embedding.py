"""add clip_embedding to photos

Revision ID: b1f2c3d4e5a6
Revises: 9cc372a7cbb6
Create Date: 2026-06-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f2c3d4e5a6'
down_revision: Union[str, None] = '9cc372a7cbb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('photos', sa.Column('clip_embedding', sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column('photos', 'clip_embedding')
