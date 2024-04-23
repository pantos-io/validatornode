import unittest.mock

import pytest

from pantos.validatornode.database.access import \
    update_transfer_source_transaction


@pytest.mark.parametrize('source_block_number', [9807193, 258289])
@pytest.mark.parametrize('source_transfer_id', [9652, 760115])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_source_transaction_correct(
        mock_get_session, database_session_maker, source_transfer_id,
        source_block_number, initialized_database_session, transfer):
    mock_get_session.return_value = database_session_maker
    initialized_database_session.add(transfer)
    initialized_database_session.commit()
    assert transfer.source_transfer_id != source_transfer_id
    assert transfer.source_block_number != source_block_number
    update_transfer_source_transaction(transfer.id, source_transfer_id,
                                       source_block_number)
    initialized_database_session.refresh(transfer)
    assert transfer.source_transfer_id == source_transfer_id
    assert transfer.source_block_number == source_block_number
