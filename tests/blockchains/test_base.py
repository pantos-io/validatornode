import tempfile
import unittest.mock
import uuid

import pytest
from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.entities import TransactionStatus

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.blockchains.base import \
    UnresolvableTransferToSubmissionError

_MOCK_CONFIG = {
    'providers': [''],
    'fallback_providers': [''],
    'average_block_time': 14,
    'confirmations': 12,
    'chain_id': 1,
    'private_key': tempfile.mkstemp()[1],
    'private_key_password': 'some_password'
}

_TRANSACTION_ID = \
    '0x5792e26d11cdf54155de59de5ddcca3f9d084ce89f4b5d4f9e50ec30c726be70'

_BLOCK_NUMBER = 8130014

_DESTINATION_TRANSFER_ID = 9372


@pytest.fixture(scope='module')
@unittest.mock.patch(
    'pantos.validatornode.blockchains.base.initialize_blockchain_utilities')
@unittest.mock.patch.object(BlockchainClient, '_get_config',
                            return_value=_MOCK_CONFIG)
@unittest.mock.patch.object(BlockchainClient, 'get_blockchain',
                            return_value=Blockchain(0))
@unittest.mock.patch.object(BlockchainClient, '__abstractmethods__', set())
def blockchain_client(mock_get_blockchain, mock_get_config,
                      mock_initialize_blockchain_utilities):
    return BlockchainClient()


@unittest.mock.patch(
    'pantos.validatornode.blockchains.base.initialize_blockchain_utilities')
@unittest.mock.patch.object(BlockchainClient, '_get_config',
                            return_value=_MOCK_CONFIG)
@unittest.mock.patch.object(BlockchainClient, 'get_blockchain',
                            return_value=Blockchain(0))
@unittest.mock.patch.object(BlockchainClient, '__abstractmethods__', set())
def test_init_correct(mock_get_blockchain, mock_get_config,
                      mock_initialize_blockchain_utilities):
    BlockchainClient()
    mock_initialize_blockchain_utilities.assert_called_once()


@unittest.mock.patch(
    'pantos.validatornode.blockchains.base.initialize_blockchain_utilities',
    side_effect=BlockchainUtilitiesError(''))
@unittest.mock.patch.object(BlockchainClient, '_create_error',
                            return_value=BlockchainClientError(''))
@unittest.mock.patch.object(BlockchainClient, '_get_config',
                            return_value=_MOCK_CONFIG)
@unittest.mock.patch.object(BlockchainClient, 'get_blockchain',
                            return_value=Blockchain(0))
@unittest.mock.patch.object(BlockchainClient, '__abstractmethods__', set())
def test_init_error(mock_get_blockchain, mock_get_config, mock_create_error,
                    mock_initialize_blockchain_utilities):
    with pytest.raises(BlockchainClientError) as exception_info:
        BlockchainClient()
    assert isinstance(exception_info.value.__context__,
                      BlockchainUtilitiesError)


@unittest.mock.patch.object(BlockchainClient, 'get_utilities')
def test_get_transfer_to_submission_status_not_completed(
        mock_get_utilities, blockchain_client):
    mock_get_utilities().get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(False)
    status_response = blockchain_client.get_transfer_to_submission_status(
        uuid.uuid4())
    assert not status_response.transaction_submission_completed


@pytest.mark.parametrize(
    'transaction_status',
    [TransactionStatus.CONFIRMED, TransactionStatus.REVERTED])
@unittest.mock.patch.object(
    BlockchainClient, '_read_transfer_to_transaction_data',
    return_value=BlockchainClient._TransferToTransactionDataResponse(
        _BLOCK_NUMBER, destination_transfer_id=_DESTINATION_TRANSFER_ID))
@unittest.mock.patch.object(BlockchainClient, 'get_utilities')
def test_get_transfer_to_submission_status_completed(
        mock_get_utilities, mock_read_transfer_to_transaction_data,
        transaction_status, blockchain_client):
    mock_get_utilities().get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(
            True, transaction_status, _TRANSACTION_ID)
    status_response = blockchain_client.get_transfer_to_submission_status(
        uuid.uuid4())
    assert status_response.transaction_submission_completed
    assert status_response.transaction_status is transaction_status
    assert status_response.transaction_id == _TRANSACTION_ID
    assert status_response.block_number == _BLOCK_NUMBER
    if transaction_status is TransactionStatus.CONFIRMED:
        assert (status_response.destination_transfer_id ==
                _DESTINATION_TRANSFER_ID)


@unittest.mock.patch.object(BlockchainClient, 'get_utilities')
@unittest.mock.patch.object(BlockchainClient, 'get_error_class',
                            return_value=BlockchainClientError)
def test_get_transfer_to_submission_status_error(mock_get_error_class,
                                                 mock_get_utilities,
                                                 blockchain_client):
    mock_get_utilities().get_transaction_submission_status.side_effect = \
        BlockchainUtilitiesError('')
    with pytest.raises(UnresolvableTransferToSubmissionError):
        blockchain_client.get_transfer_to_submission_status(uuid.uuid4())
