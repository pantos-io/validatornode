import unittest.mock

from pantos.validatornode.database.access import \
    update_transfer_confirmed_destination_transaction
from tests.database.utilities import modify_model_instance


@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_update_transfer_destination_transaction_correct(
        mock_get_session, mock_get_session_maker,
        initialized_database_session_maker, transfer,
        other_destination_transfer_id, other_destination_transaction_id,
        other_destination_block_number):
    initialized_database_session = initialized_database_session_maker()
    mock_get_session.return_value = initialized_database_session
    mock_get_session_maker.return_value = initialized_database_session_maker
    transfer = modify_model_instance(transfer, destination_transfer_id=None,
                                     destination_block_number=None)
    initialized_database_session.add(transfer)
    initialized_database_session.commit()
    update_transfer_confirmed_destination_transaction(
        transfer.id, other_destination_transfer_id,
        other_destination_transaction_id, other_destination_block_number)
    initialized_database_session.refresh(transfer)
    assert transfer.destination_transfer_id == other_destination_transfer_id
    assert (transfer.destination_transaction_id ==
            other_destination_transaction_id)
    assert transfer.destination_block_number == other_destination_block_number
