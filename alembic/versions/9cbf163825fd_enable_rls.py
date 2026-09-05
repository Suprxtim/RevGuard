"""enable_rls

Revision ID: 9cbf163825fd
Revises: 8bfc37aa5046
Create Date: 2026-09-02 01:30:28.966177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cbf163825fd'
down_revision: Union[str, None] = '8bfc37aa5046'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
