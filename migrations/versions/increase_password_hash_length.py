"""increase password hash length

Revision ID: increase_password_hash_length
Revises: cde96cf870be
Create Date: 2024-03-03 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'increase_password_hash_length'
down_revision = 'cde96cf870be'
branch_labels = None
depends_on = None

def upgrade():
    # PostgreSQL için özel komut
    op.execute('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255) USING password_hash::VARCHAR(255)')

def downgrade():
    # PostgreSQL için özel komut
    op.execute('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(128) USING password_hash::VARCHAR(128)') 