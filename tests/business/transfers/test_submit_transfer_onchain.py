import unittest.mock
import uuid

import celery.exceptions  # type: ignore
import pytest

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import NonMatchingForwarderError
from pantos.validatornode.blockchains.base import \
    SourceTransferIdAlreadyUsedError
from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.business.transfers import \
    submit_transfer_onchain_task
from pantos.validatornode.database.enums import TransferStatus

_INTERNAL_TRANSACTION_ID = uuid.uuid4()

_DESTINATION_HUB_ADDRESS = '0xc4FE8209798A8fF786555fE3f2E6d1e56b851860'

_DESTINATION_FORWARDER_ADDRESS = '0xb3D0CC89843Bf92ED3Bcc66143C7De744f58557B'

_VALIDATOR_NONCE = 1488942604520


@pytest.fixture
def transfer_to_submission_start_response():
    return BlockchainClient.TransferToSubmissionStartResponse(
        _INTERNAL_TRANSACTION_ID, _DESTINATION_HUB_ADDRESS,
        _DESTINATION_FORWARDER_ADDRESS)


@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_submit_transfer_onchain_correct(
        mock_get_blockchain_client, mock_database_access,
        mock_confirm_transfer_task, is_reversal_transfer, transfer_interactor,
        internal_transfer_id, cross_chain_transfer,
        transfer_to_submission_start_response):
    mock_get_blockchain_client().start_transfer_to_submission.return_value = \
        transfer_to_submission_start_response
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = _VALIDATOR_NONCE
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    submission_completed = transfer_interactor.submit_transfer_onchain(
        internal_transfer_id, cross_chain_transfer)

    assert submission_completed
    mock_get_blockchain_client().start_transfer_to_submission.\
        assert_called_once_with(
            BlockchainClient.TransferToSubmissionStartRequest(
                internal_transfer_id, cross_chain_transfer,
                _VALIDATOR_NONCE))
    destination_hub_address = \
        transfer_to_submission_start_response.destination_hub_address
    destination_forwarder_address = \
        transfer_to_submission_start_response.destination_forwarder_address
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_called_once_with(
            internal_transfer_id,
            destination_hub_address,
            destination_forwarder_address)
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id,
        TransferStatus.SOURCE_REVERSAL_TRANSACTION_SUBMITTED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_SUBMITTED)
    mock_confirm_transfer_task.delay.assert_called_once_with(
        internal_transfer_id,
        str(transfer_to_submission_start_response.internal_transaction_id),
        cross_chain_transfer.to_dict())


@pytest.mark.parametrize(
    'start_transfer_to_submission_side_effect',
    [NonMatchingForwarderError, SourceTransferIdAlreadyUsedError])
@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_submit_transfer_onchain_permanent_on_chain_verification_error_correct(
        mock_get_blockchain_client, mock_database_access,
        mock_confirm_transfer_task, is_reversal_transfer,
        start_transfer_to_submission_side_effect, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    mock_get_blockchain_client().start_transfer_to_submission.side_effect = \
        start_transfer_to_submission_side_effect
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = _VALIDATOR_NONCE
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    submission_completed = transfer_interactor.submit_transfer_onchain(
        internal_transfer_id, cross_chain_transfer)

    assert submission_completed
    mock_get_blockchain_client().start_transfer_to_submission.\
        assert_called_once_with(
            BlockchainClient.TransferToSubmissionStartRequest(
                internal_transfer_id, cross_chain_transfer, _VALIDATOR_NONCE))
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_not_called()
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_FAILED)
    mock_confirm_transfer_task.delay.assert_not_called()


@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_submit_transfer_onchain_transfer_to_error(
        mock_get_blockchain_client, mock_database_access,
        mock_confirm_transfer_task, is_reversal_transfer, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    mock_get_blockchain_client().start_transfer_to_submission.side_effect = \
        Exception
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = _VALIDATOR_NONCE
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.submit_transfer_onchain(internal_transfer_id,
                                                    cross_chain_transfer)

    assert (exception_info.value.details['internal_transfer_id'] ==
            internal_transfer_id)
    assert (exception_info.value.details['transfer'] == cross_chain_transfer)
    mock_get_blockchain_client().start_transfer_to_submission.\
        assert_called_once_with(
            BlockchainClient.TransferToSubmissionStartRequest(
                internal_transfer_id, cross_chain_transfer, _VALIDATOR_NONCE))
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_not_called()
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_FAILED)
    mock_confirm_transfer_task.delay.assert_not_called()


@pytest.mark.parametrize('submission_completed', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config',
    {'tasks': {
        'submit_transfer_onchain': {
            'retry_interval_in_seconds': 120
        }
    }})
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_submit_transfer_onchain_task_correct(mock_transfer_interactor,
                                              submission_completed,
                                              internal_transfer_id,
                                              cross_chain_transfer,
                                              cross_chain_transfer_dict):
    mock_transfer_interactor().submit_transfer_onchain.return_value = \
        submission_completed
    if submission_completed:
        submit_transfer_onchain_task(internal_transfer_id,
                                     cross_chain_transfer_dict)
    else:
        with pytest.raises(celery.exceptions.Retry):
            submit_transfer_onchain_task(internal_transfer_id,
                                         cross_chain_transfer_dict)
    mock_transfer_interactor().submit_transfer_onchain.assert_called_once_with(
        internal_transfer_id, cross_chain_transfer)


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config', {
        'tasks': {
            'submit_transfer_onchain': {
                'retry_interval_after_error_in_seconds': 300
            }
        }
    })
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_submit_transfer_onchain_task_error(mock_transfer_interactor,
                                            internal_transfer_id,
                                            cross_chain_transfer,
                                            cross_chain_transfer_dict):
    mock_transfer_interactor().submit_transfer_onchain.side_effect = \
        TransferInteractorError('')
    with pytest.raises(TransferInteractorError):
        submit_transfer_onchain_task(internal_transfer_id,
                                     cross_chain_transfer_dict)
    mock_transfer_interactor().submit_transfer_onchain.assert_called_once_with(
        internal_transfer_id, cross_chain_transfer)
