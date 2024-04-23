import unittest.mock

import pytest

from pantos.validatornode.database.access import update_transfer_status
from pantos.validatornode.database.enums import TransferStatus


@pytest.mark.parametrize('new_transfer_status', TransferStatus)
@pytest.mark.parametrize('old_transfer_status', TransferStatus)
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_status_correct(
        mock_get_session, database_session_maker, old_transfer_status,
        new_transfer_status, initialized_database_session, transfer):
    mock_get_session.return_value = database_session_maker
    transfer.status_id = old_transfer_status.value
    initialized_database_session.add(transfer)
    initialized_database_session.commit()
    update_transfer_status(transfer.id, new_transfer_status)
    initialized_database_session.refresh(transfer)
    assert transfer.status_id == new_transfer_status.value
