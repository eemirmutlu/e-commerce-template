"""increase password hash length

Revision ID: increase_password_hash_length
Revises: add_cvv_field
Create Date: 2024-03-03 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'increase_password_hash_length'
down_revision = 'add_cvv_field'
branch_labels = None
depends_on = None

def upgrade():
    # PostgreSQL için
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255)')
    # SQLite için
    else:
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('password_hash',
                                existing_type=sa.String(length=128),
                                type_=sa.String(length=255),
                                existing_nullable=True)

def downgrade():
    # PostgreSQL için
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(128)')
    # SQLite için
    else:
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('password_hash',
                                existing_type=sa.String(length=255),
                                type_=sa.String(length=128),
                                existing_nullable=True) 