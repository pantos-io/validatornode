"""validator_nonce_not_nullable

Revision ID: 536e50b24e1f
Revises: d10f1f88af0f
Create Date: 2024-05-07 09:13:52.815356

"""
import alembic
import sqlalchemy

# revision identifiers, used by Alembic.
revision = '536e50b24e1f'
down_revision = 'd10f1f88af0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    alembic.op.execute('UPDATE transfers SET validator_nonce = id '
                       'WHERE validator_nonce IS NULL')
    alembic.op.alter_column(
        'transfers', 'validator_nonce',
        existing_type=sqlalchemy.NUMERIC(precision=78,
                                         scale=0), nullable=False)


def downgrade() -> None:
    alembic.op.alter_column(
        'transfers', 'validator_nonce',
        existing_type=sqlalchemy.NUMERIC(precision=78, scale=0), nullable=True)
