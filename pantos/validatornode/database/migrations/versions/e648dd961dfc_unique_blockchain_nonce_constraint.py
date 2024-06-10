"""unique_blockchain_nonce_constraint

Revision ID: e648dd961dfc
Revises: 536e50b24e1f
Create Date: 2024-06-06 04:13:50.740664

"""
import alembic

# revision identifiers, used by Alembic.
revision = 'e648dd961dfc'
down_revision = '536e50b24e1f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    alembic.op.execute('UPDATE transfers SET nonce = NULL')
    alembic.op.create_unique_constraint('unique_blockchain_nonce', 'transfers',
                                        ['destination_blockchain_id', 'nonce'],
                                        deferrable='True')


def downgrade() -> None:
    alembic.op.drop_constraint('unique_blockchain_nonce', 'transfers',
                               type_='unique')
