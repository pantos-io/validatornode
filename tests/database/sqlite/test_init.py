import itertools
import unittest.mock

import pytest
import sqlalchemy.exc
import sqlalchemy.orm
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database import get_session
from pantos.validatornode.database import get_session_maker
from pantos.validatornode.database import initialize_package
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.exceptions import DatabaseError
from pantos.validatornode.database.models import Blockchain as Blockchain_
from pantos.validatornode.database.models import \
    TransferStatus as TransferStatus_

_DATABASE_CONFIG = {
    'database': {
        'url': '',
        'pool_size': None,
        'max_overflow': None,
        'echo': None,
        'alembic_config': '/path/to/alembic.ini',
        'apply_migrations': True
    }
}


def test_get_session_maker_correct(database_session_maker):
    with unittest.mock.patch('pantos.validatornode.database._session_maker',
                             database_session_maker):
        assert get_session_maker() == database_session_maker


def test_get_session_maker_database_error():
    with pytest.raises(DatabaseError):
        get_session_maker()


def test_get_session_correct(database_session_maker):
    with unittest.mock.patch('pantos.validatornode.database._session_maker',
                             database_session_maker):
        assert isinstance(get_session(), sqlalchemy.orm.Session)


def test_get_session_database_error():
    with pytest.raises(DatabaseError):
        get_session()


@pytest.mark.parametrize('is_flask_app', [True, False])
@pytest.mark.parametrize(
    'existing_transfer_statuses',
    itertools.chain.from_iterable(
        itertools.combinations(TransferStatus, r) for r in range(2)))
@pytest.mark.parametrize(
    'existing_blockchains',
    itertools.chain.from_iterable(
        itertools.combinations(Blockchain, r) for r in range(2)))
@unittest.mock.patch('pantos.validatornode.database.config', _DATABASE_CONFIG)
@unittest.mock.patch('pantos.validatornode.database.sqlalchemy.create_engine')
@unittest.mock.patch('alembic.command.upgrade')
@unittest.mock.patch('alembic.config.Config')
def test_initialize_package_correct(mock_config, mock_upgrade,
                                    mock_create_engine, existing_blockchains,
                                    existing_transfer_statuses, is_flask_app,
                                    database_engine, database_session):
    for blockchain in existing_blockchains:
        database_session.execute(
            sqlalchemy.insert(Blockchain_).values(id=blockchain.value,
                                                  name=blockchain.name))
    for transfer_status in existing_transfer_statuses:
        database_session.execute(
            sqlalchemy.insert(TransferStatus_).values(
                id=transfer_status.value, name=transfer_status.name))
    database_session.commit()
    mock_create_engine.return_value = database_engine

    initialize_package(is_flask_app)

    blockchain_records = database_session.execute(
        sqlalchemy.select(Blockchain_)).fetchall()
    assert len(blockchain_records) == (len(Blockchain) if is_flask_app else
                                       len(existing_blockchains))
    blockchains = {blockchain.value: blockchain for blockchain in Blockchain}
    for blockchain_record in blockchain_records:
        blockchain = blockchains.pop(blockchain_record[0].id)
        assert blockchain_record[0].name == blockchain.name
    transfer_status_records = database_session.execute(
        sqlalchemy.select(TransferStatus_)).fetchall()
    assert len(transfer_status_records) == (len(TransferStatus)
                                            if is_flask_app else
                                            len(existing_transfer_statuses))
    transfer_statuses = {
        transfer_status.value: transfer_status
        for transfer_status in TransferStatus
    }
    for transfer_status_record in transfer_status_records:
        transfer_status = transfer_statuses.pop(transfer_status_record[0].id)
        assert transfer_status_record[0].name == transfer_status.name
