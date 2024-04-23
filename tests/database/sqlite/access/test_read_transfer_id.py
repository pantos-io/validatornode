import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.access import read_transfer_id


@pytest.mark.parametrize('transfer_existent', [True, False])
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_read_transfer_id_correct(mock_get_session, database_session_maker,
                                  transfer_existent,
                                  initialized_database_session, transfer):
    mock_get_session.side_effect = database_session_maker
    if transfer_existent:
        initialized_database_session.add(transfer)
        initialized_database_session.commit()
    internal_transfer_id = read_transfer_id(
        Blockchain(transfer.source_blockchain_id),
        transfer.source_transaction_id)
    assert internal_transfer_id == (transfer.id if transfer_existent else None)
