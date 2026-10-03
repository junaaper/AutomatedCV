"""drop the HNSW index on cv chunks

Searches are always scoped to one user's chunks, where exact KNN via the user_id index is
correct and fast. The approximate index applied the user filter after collecting global
candidates, so other users' chunks could crowd out all of a user's results.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_cv_chunks_embedding_hnsw", table_name="cv_chunks")


def downgrade() -> None:
    op.create_index(
        "ix_cv_chunks_embedding_hnsw",
        "cv_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
