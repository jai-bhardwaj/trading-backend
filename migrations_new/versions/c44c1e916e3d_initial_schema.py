"""Initial schema

Revision ID: c44c1e916e3d
Revises: 
Create Date: 2023-05-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c44c1e916e3d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE strategystatus AS ENUM ('active', 'inactive')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('pending', 'completed', 'cancelled', 'rejected')")
    op.execute("CREATE TYPE ordertype AS ENUM ('buy', 'sell')")
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=True)
    
    # Create strategies table
    op.create_table('strategies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('margin', sa.Float(), nullable=False),
        sa.Column('marginType', sa.String(), nullable=False),
        sa.Column('basePrice', sa.Float(), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'inactive', name='strategystatus'), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('lastUpdated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategies_id'), 'strategies', ['id'], unique=True)
    op.create_index(op.f('ix_strategies_name'), 'strategies', ['name'], unique=False)
    op.create_index(op.f('ix_strategies_symbol'), 'strategies', ['symbol'], unique=False)
    
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('order_type', postgresql.ENUM('buy', 'sell', name='ordertype'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'completed', 'cancelled', 'rejected', name='orderstatus'), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('exchange_order_id', sa.String(), nullable=True),
        sa.Column('exchange_status', sa.String(), nullable=True),
        sa.Column('exchange_message', sa.String(), nullable=True),
        sa.Column('order_time', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=True)
    op.create_index(op.f('ix_orders_symbol'), 'orders', ['symbol'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_orders_symbol'), table_name='orders')
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_strategies_symbol'), table_name='strategies')
    op.drop_index(op.f('ix_strategies_name'), table_name='strategies')
    op.drop_index(op.f('ix_strategies_id'), table_name='strategies')
    op.drop_table('strategies')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("DROP TYPE ordertype")
    op.execute("DROP TYPE orderstatus")
    op.execute("DROP TYPE strategystatus") 