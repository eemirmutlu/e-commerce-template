"""increase password hash length

Revision ID: increase_password_hash_length
Revises: add_cvv_field
Create Date: 2024-03-03 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'increase_password_hash_length'
down_revision = 'add_cvv_field'
branch_labels = None
depends_on = None

def upgrade():
    # PostgreSQL'de VARCHAR uzunluğunu artır
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(length=128),
                    type_=sa.String(length=255),
                    existing_nullable=True)

def downgrade():
    # Eski haline döndür
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(length=255),
                    type_=sa.String(length=128),
                    existing_nullable=True) 