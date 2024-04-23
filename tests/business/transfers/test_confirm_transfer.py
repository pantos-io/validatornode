import unittest.mock
import uuid

import celery.exceptions  # type: ignore
import pytest
from pantos.common.entities import TransactionStatus

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import \
    UnresolvableTransferToSubmissionError
from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.business.transfers import confirm_transfer_task
from pantos.validatornode.database.enums import TransferStatus

_INTERNAL_TRANSACTION_ID = uuid.uuid4()

_DESTINATION_TRANSFER_ID = 55409

_DESTINATION_TRANSACTION_ID = \
    '0x82f5a0189d88bd241064a4a1f346826d99f613ccbe41abb0c18f2d8739ca03f6'

_DESTINATION_BLOCK_NUMBER = 170842


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_confirm_transfer_unconfirmed_correct(mock_get_blockchain_client,
                                              transfer_interactor,
                                              internal_transfer_id,
                                              cross_chain_transfer):
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_client.get_transfer_to_submission_status.return_value = \
        BlockchainClient.TransferToSubmissionStatusResponse(False)
    confirmation_completed = transfer_interactor.confirm_transfer(
        internal_transfer_id, _INTERNAL_TRANSACTION_ID, cross_chain_transfer)
    assert not confirmation_completed


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.validate_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_confirm_transfer_reverted_correct(
        mock_get_blockchain_client, mock_database_access,
        mock_validate_transfer_task, transfer_interactor, internal_transfer_id,
        cross_chain_transfer, cross_chain_transfer_dict):
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_client.get_transfer_to_submission_status.return_value = \
        BlockchainClient.TransferToSubmissionStatusResponse(
            True, TransactionStatus.REVERTED, _DESTINATION_TRANSACTION_ID,
            _DESTINATION_BLOCK_NUMBER)
    mock_validate_transfer_task.delay().id = str(uuid.uuid4())
    mock_validate_transfer_task.delay.call_count = 0
    confirmation_completed = transfer_interactor.confirm_transfer(
        internal_transfer_id, _INTERNAL_TRANSACTION_ID, cross_chain_transfer)
    assert confirmation_completed
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_TRANSACTION_DETECTED)
    mock_database_access.reset_transfer_nonce.assert_called_once_with(
        internal_transfer_id)
    mock_database_access.update_transfer_task_id.assert_called_once()
    mock_validate_transfer_task.delay.assert_called_once_with(
        internal_transfer_id, cross_chain_transfer_dict)


@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_confirm_transfer_confirmed_correct(
        mock_get_blockchain_client, mock_database_access, is_reversal_transfer,
        transfer_interactor, internal_transfer_id, cross_chain_transfer):
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_client.get_transfer_to_submission_status.return_value = \
        BlockchainClient.TransferToSubmissionStatusResponse(
            True, TransactionStatus.CONFIRMED, _DESTINATION_TRANSACTION_ID,
            _DESTINATION_BLOCK_NUMBER,
            destination_transfer_id=_DESTINATION_TRANSFER_ID)
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer
    confirmation_completed = transfer_interactor.confirm_transfer(
        internal_transfer_id, _INTERNAL_TRANSACTION_ID, cross_chain_transfer)
    assert confirmation_completed
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id,
        TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_CONFIRMED)


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.validate_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_confirm_transfer_unresolvable_error(
        mock_get_blockchain_client, mock_database_access,
        mock_validate_transfer_task, transfer_interactor, internal_transfer_id,
        cross_chain_transfer, cross_chain_transfer_dict):
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_client.get_transfer_to_submission_status.side_effect = \
        UnresolvableTransferToSubmissionError
    mock_validate_transfer_task.delay().id = str(uuid.uuid4())
    mock_validate_transfer_task.delay.call_count = 0
    confirmation_completed = transfer_interactor.confirm_transfer(
        internal_transfer_id, _INTERNAL_TRANSACTION_ID, cross_chain_transfer)
    assert confirmation_completed
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_TRANSACTION_DETECTED)
    mock_database_access.reset_transfer_nonce.assert_called_once_with(
        internal_transfer_id)
    mock_database_access.update_transfer_task_id.assert_called_once()
    mock_validate_transfer_task.delay.assert_called_once_with(
        internal_transfer_id, cross_chain_transfer_dict)


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client',
    side_effect=Exception)
def test_confirm_transfer_error(mock_get_blockchain_client,
                                transfer_interactor, internal_transfer_id,
                                cross_chain_transfer):
    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.confirm_transfer(internal_transfer_id,
                                             _INTERNAL_TRANSACTION_ID,
                                             cross_chain_transfer)
    assert (exception_info.value.details['internal_transfer_id'] ==
            internal_transfer_id)
    assert (exception_info.value.details['internal_transaction_id'] ==
            _INTERNAL_TRANSACTION_ID)
    assert exception_info.value.details['transfer'] == cross_chain_transfer


@pytest.mark.parametrize('confirmation_completed', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config',
    {'tasks': {
        'confirm_transfer': {
            'retry_interval_in_seconds': 120
        }
    }})
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_confirm_transfer_task_correct(mock_transfer_interactor,
                                       confirmation_completed,
                                       internal_transfer_id,
                                       cross_chain_transfer,
                                       cross_chain_transfer_dict):
    mock_transfer_interactor().confirm_transfer.return_value = \
        confirmation_completed
    if confirmation_completed:
        confirm_transfer_task(internal_transfer_id,
                              str(_INTERNAL_TRANSACTION_ID),
                              cross_chain_transfer_dict)
    else:
        with pytest.raises(celery.exceptions.Retry):
            confirm_transfer_task(internal_transfer_id,
                                  str(_INTERNAL_TRANSACTION_ID),
                                  cross_chain_transfer_dict)
    mock_transfer_interactor().confirm_transfer.assert_called_once_with(
        internal_transfer_id, _INTERNAL_TRANSACTION_ID, cross_chain_transfer)


@unittest.mock.patch('pantos.validatornode.business.transfers.config', {
    'tasks': {
        'confirm_transfer': {
            'retry_interval_after_error_in_seconds': 300
        }
    }
})
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_confirm_transfer_task_error(mock_transfer_interactor,
                                     internal_transfer_id,
                                     cross_chain_transfer,
                                     cross_chain_transfer_dict):
    mock_transfer_interactor().confirm_transfer.side_effect = \
        TransferInteractorError('')
    with pytest.raises(TransferInteractorError):
        confirm_transfer_task(internal_transfer_id,
                              str(_INTERNAL_TRANSACTION_ID),
                              cross_chain_transfer_dict)
    mock_transfer_interactor().confirm_transfer.assert_called_once_with(
        internal_transfer_id, _INTERNAL_TRANSACTION_ID, cross_chain_transfer)
