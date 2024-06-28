import datetime
import unittest.mock

import sqlalchemy.orm

from pantos.validatornode.database.access import \
    update_transfer_validator_nonce


@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_validator_nonce_correct(
        mock_get_session_maker, initialized_database_session_maker, transfer,
        other_validator_nonce):
    assert transfer.validator_nonce != other_validator_nonce
    mock_get_session_maker.return_value = initialized_database_session_maker
    initialized_database_session = initialized_database_session_maker()
    initialized_database_session.add(transfer)
    initialized_database_session.commit()
    transfer_dict = {
        key: value
        for key, value in vars(transfer).items() if key != 'validator_nonce'
        and not isinstance(value, sqlalchemy.orm.state.InstanceState)
    }
    date_time_before_update = datetime.datetime.now(datetime.timezone.utc)

    update_transfer_validator_nonce(transfer.id, other_validator_nonce)

    date_time_after_update = datetime.datetime.now(datetime.timezone.utc)
    initialized_database_session.refresh(transfer)
    assert transfer.validator_nonce == other_validator_nonce
    assert transfer.updated > date_time_before_update.replace(tzinfo=None)
    assert transfer.updated < date_time_after_update.replace(tzinfo=None)
    updated_transfer_dict = vars(transfer)
    for key, value in transfer_dict.items():
        assert updated_transfer_dict[key] == value
