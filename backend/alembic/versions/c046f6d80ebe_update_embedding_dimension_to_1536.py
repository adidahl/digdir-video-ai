"""update_embedding_dimension_to_1536

Revision ID: c046f6d80ebe
Revises: 
Create Date: 2025-12-05 17:46:24.481217

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c046f6d80ebe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update embedding column dimension from 1024 to 1536 to match OpenAI's text-embedding-ada-002
    op.execute("""
        ALTER TABLE video_segments 
        ALTER COLUMN embedding TYPE vector(1536);
    """)


def downgrade() -> None:
    # Revert to 1024 dimensions (note: this will truncate vectors!)
    op.execute("""
        ALTER TABLE video_segments 
        ALTER COLUMN embedding TYPE vector(1024);
    """)

