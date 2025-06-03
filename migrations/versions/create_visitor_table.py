"""Create visitor table

Revision ID: create_visitor_table
Revises: fix_password_hash_length_postgres
Create Date: 2024-03-03 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_visitor_table'
down_revision = 'fix_password_hash_length_postgres'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('visitor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('last_visit', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('visitor') 