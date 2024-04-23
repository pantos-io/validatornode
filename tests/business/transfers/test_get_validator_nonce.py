import unittest.mock

import pytest

from pantos.validatornode.business.base import UnknownTransferError
from pantos.validatornode.business.transfers import TransferInteractorError


@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
def test_get_validator_nonce_correct(mock_database_access, source_blockchain,
                                     source_transaction_id, validator_nonce,
                                     transfer_interactor):
    mock_database_access.read_validator_nonce_by_source_transaction_id.\
        return_value = validator_nonce

    result = transfer_interactor.get_validator_nonce(source_blockchain,
                                                     source_transaction_id)

    assert result == validator_nonce


@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
def test_get_validator_nonce_unknown_transfer_error(mock_database_access,
                                                    source_blockchain,
                                                    source_transaction_id,
                                                    transfer_interactor):
    mock_database_access.read_transfer_id.return_value = None
    mock_database_access.read_validator_nonce_by_source_transaction_id.\
        return_value = None

    with pytest.raises(UnknownTransferError) as exception_info:
        transfer_interactor.get_validator_nonce(source_blockchain,
                                                source_transaction_id)

    assert isinstance(exception_info.value, TransferInteractorError)


@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
def test_get_validator_nonce_database_error(mock_database_access,
                                            source_blockchain,
                                            source_transaction_id,
                                            transfer_interactor):
    mock_database_access.read_validator_nonce_by_source_transaction_id.\
        side_effect = Exception

    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.get_validator_nonce(source_blockchain,
                                                source_transaction_id)

    assert not isinstance(exception_info.value, UnknownTransferError)
