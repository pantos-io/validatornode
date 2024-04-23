import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.access import \
    update_blockchain_last_block_number
from pantos.validatornode.database.exceptions import DatabaseError


@pytest.mark.parametrize('new_last_block_number', [586258, 818775])
@pytest.mark.parametrize('old_last_block_number', [316623, 586258])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_blockchain_last_block_number_correct(
        mock_get_session, database_session_maker, old_last_block_number,
        new_last_block_number, database_session, blockchain):
    mock_get_session.return_value = database_session_maker
    blockchain.last_block_number = old_last_block_number
    database_session.add(blockchain)
    database_session.commit()
    update_blockchain_last_block_number(Blockchain(blockchain.id),
                                        new_last_block_number)
    database_session.refresh(blockchain)
    assert blockchain.last_block_number == new_last_block_number


@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_blockchain_last_block_number_database_error(
        mock_get_session, database_session_maker, database_session,
        blockchain):
    mock_get_session.return_value = database_session_maker
    blockchain.last_block_number = 734590
    database_session.add(blockchain)
    database_session.commit()
    with pytest.raises(DatabaseError):
        update_blockchain_last_block_number(Blockchain(blockchain.id), 529483)
