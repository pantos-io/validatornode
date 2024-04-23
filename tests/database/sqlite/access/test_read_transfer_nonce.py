import unittest.mock

import pytest

from pantos.validatornode.database.access import read_transfer_nonce


@pytest.mark.parametrize('nonce', [888643, 4094])
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_read_transfer_nonce_correct(mock_get_session, database_session_maker,
                                     nonce, initialized_database_session,
                                     transfer):
    mock_get_session.side_effect = database_session_maker
    transfer.nonce = nonce
    initialized_database_session.add(transfer)
    initialized_database_session.commit()
    read_nonce = read_transfer_nonce(transfer.id)
    assert read_nonce == nonce
