"""fix password hash length for postgresql

Revision ID: fix_password_hash_length_postgres
Revises: fix_password_hash_length
Create Date: 2024-03-03 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_password_hash_length_postgres'
down_revision = 'fix_password_hash_length'
branch_labels = None
depends_on = None

def upgrade():
    # PostgreSQL için özel komut
    op.execute('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255) USING password_hash::VARCHAR(255)')

def downgrade():
    # PostgreSQL için özel komut
    op.execute('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(128) USING password_hash::VARCHAR(128)') 