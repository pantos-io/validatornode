import unittest.mock

from pantos.validatornode.database.access import reset_transfer_nonce


@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_reset_transfer_nonce_correct(mock_get_session_maker,
                                      initialized_database_session_maker,
                                      transfer):
    mock_get_session_maker.return_value = initialized_database_session_maker
    if transfer.nonce is None:
        transfer.nonce = 3323
    with initialized_database_session_maker() as database_session:
        database_session.add(transfer)
        database_session.commit()
        reset_transfer_nonce(transfer.id)
        database_session.refresh(transfer)
    assert transfer.nonce is None
