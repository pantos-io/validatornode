import unittest.mock
import uuid

import celery.exceptions  # type: ignore
import pytest

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.blockchains.base import NonMatchingForwarderError
from pantos.validatornode.blockchains.base import \
    SourceTransferIdAlreadyUsedError
from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.business.transfers import \
    submit_transfer_onchain_task
from pantos.validatornode.database.enums import TransferStatus

_INTERNAL_TRANSACTION_ID = uuid.uuid4()


@pytest.mark.parametrize('available_validator_node_signatures', range(3, 5))
@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'primary'
                     }})
def test_submit_transfer_onchain_sufficient_signatures_correct(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_database_access, mock_confirm_transfer_task, is_reversal_transfer,
        available_validator_node_signatures, transfer_interactor,
        internal_transfer_id, cross_chain_transfer, validator_nonce,
        destination_hub_address, destination_forwarder_address,
        minimum_validator_node_signatures, validator_node_signatures):
    mock_get_blockchain_config.return_value = {
        'hub': destination_hub_address,
        'forwarder': destination_forwarder_address
    }
    assert (available_validator_node_signatures
            >= minimum_validator_node_signatures)
    assert (available_validator_node_signatures
            <= len(validator_node_signatures))
    unavailable_addresses = list(
        validator_node_signatures.keys())[available_validator_node_signatures:]
    for unavailable_address in unavailable_addresses:
        validator_node_signatures.pop(unavailable_address)
    primary_node_address = list(validator_node_signatures.keys())[0]
    primary_node_signature = list(validator_node_signatures.values())[0]
    secondary_node_addresses = list(validator_node_signatures.keys())[1:]
    mock_get_blockchain_client().get_own_address.return_value = \
        primary_node_address
    mock_get_blockchain_client().is_equal_address = lambda x, y: x == y
    mock_get_blockchain_client().read_minimum_validator_node_signatures.\
        return_value = minimum_validator_node_signatures
    mock_get_blockchain_client().recover_transfer_to_signer_address.\
        side_effect = secondary_node_addresses
    mock_get_blockchain_client().sign_transfer_to_message.return_value = \
        primary_node_signature
    mock_get_blockchain_client().start_transfer_to_submission.return_value = \
        _INTERNAL_TRANSACTION_ID
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = validator_nonce
    mock_database_access.read_validator_node_signatures.return_value = \
        validator_node_signatures
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    submission_completed = transfer_interactor.submit_transfer_onchain(
        internal_transfer_id, cross_chain_transfer)

    assert submission_completed
    mock_get_blockchain_client().start_transfer_to_submission.\
        assert_called_once_with(
            BlockchainClient.TransferToSubmissionStartRequest(
                internal_transfer_id, cross_chain_transfer, validator_nonce,
                validator_node_signatures))
    mock_database_access.create_validator_node_signature.\
        assert_called_once_with(
            internal_transfer_id,
            cross_chain_transfer.eventual_destination_blockchain,
            destination_forwarder_address, primary_node_address,
            primary_node_signature)
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_called_once_with(internal_transfer_id, destination_hub_address,
                                destination_forwarder_address)
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id,
        TransferStatus.SOURCE_REVERSAL_TRANSACTION_SUBMITTED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_SUBMITTED)
    mock_confirm_transfer_task.delay.assert_called_once_with(
        internal_transfer_id, str(_INTERNAL_TRANSACTION_ID),
        cross_chain_transfer.to_dict())


@pytest.mark.parametrize('recover_signer_address_error', [True, False])
@pytest.mark.parametrize('available_validator_node_signatures', range(1, 3))
@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'primary'
                     }})
def test_submit_transfer_onchain_insufficient_signatures_correct(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_database_access, mock_confirm_transfer_task, is_reversal_transfer,
        available_validator_node_signatures, recover_signer_address_error,
        transfer_interactor, internal_transfer_id, cross_chain_transfer,
        validator_nonce, destination_hub_address,
        destination_forwarder_address, minimum_validator_node_signatures,
        validator_node_signatures):
    mock_get_blockchain_config.return_value = {
        'hub': destination_hub_address,
        'forwarder': destination_forwarder_address
    }
    assert (available_validator_node_signatures
            < minimum_validator_node_signatures)
    assert (available_validator_node_signatures
            <= len(validator_node_signatures))
    unavailable_addresses = list(
        validator_node_signatures.keys())[available_validator_node_signatures:]
    for unavailable_address in unavailable_addresses:
        validator_node_signatures.pop(unavailable_address)
    primary_node_address = list(validator_node_signatures.keys())[0]
    primary_node_signature = list(validator_node_signatures.values())[0]
    secondary_node_addresses = ([] if available_validator_node_signatures == 1
                                else list(
                                    validator_node_signatures.keys())[1:])
    mock_get_blockchain_client().get_own_address.return_value = \
        primary_node_address
    mock_get_blockchain_client().is_equal_address = lambda x, y: x == y
    mock_get_blockchain_client().read_minimum_validator_node_signatures.\
        return_value = minimum_validator_node_signatures
    mock_get_blockchain_client().recover_transfer_to_signer_address.\
        side_effect = (BlockchainClientError('') if
                       recover_signer_address_error else
                       secondary_node_addresses)
    mock_get_blockchain_client().sign_transfer_to_message.return_value = \
        primary_node_signature
    mock_get_blockchain_client().start_transfer_to_submission.return_value = \
        _INTERNAL_TRANSACTION_ID
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = validator_nonce
    mock_database_access.read_validator_node_signatures.return_value = \
        validator_node_signatures
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    submission_completed = transfer_interactor.submit_transfer_onchain(
        internal_transfer_id, cross_chain_transfer)

    assert not submission_completed
    mock_get_blockchain_client().start_transfer_to_submission.\
        assert_not_called()
    mock_database_access.create_validator_node_signature.assert_not_called()
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_not_called()
    mock_database_access.update_transfer_status.assert_not_called()
    mock_confirm_transfer_task.delay.assert_not_called()


@pytest.mark.parametrize(
    'start_transfer_to_submission_side_effect',
    [NonMatchingForwarderError, SourceTransferIdAlreadyUsedError])
@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch.object(
    TransferInteractor,
    '_TransferInteractor__sufficient_secondary_node_signatures',
    return_value=True)
@unittest.mock.patch.object(TransferInteractor,
                            '_TransferInteractor__add_primary_node_signature')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'primary'
                     }})
def test_submit_transfer_onchain_permanent_on_chain_verification_error_correct(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_database_access, mock_confirm_transfer_task,
        mock_add_primary_node_signature,
        mock_sufficient_secondary_node_signatures, is_reversal_transfer,
        start_transfer_to_submission_side_effect, transfer_interactor,
        internal_transfer_id, cross_chain_transfer, validator_nonce,
        destination_hub_address, destination_forwarder_address,
        validator_node_signatures):
    mock_get_blockchain_config.return_value = {
        'hub': destination_hub_address,
        'forwarder': destination_forwarder_address
    }
    mock_get_blockchain_client().start_transfer_to_submission.side_effect = \
        start_transfer_to_submission_side_effect
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = validator_nonce
    mock_database_access.read_validator_node_signatures.return_value = \
        validator_node_signatures
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    submission_completed = transfer_interactor.submit_transfer_onchain(
        internal_transfer_id, cross_chain_transfer)

    assert submission_completed
    mock_get_blockchain_client().start_transfer_to_submission.\
        assert_called_once_with(
            BlockchainClient.TransferToSubmissionStartRequest(
                internal_transfer_id, cross_chain_transfer, validator_nonce,
                validator_node_signatures))
    mock_database_access.create_validator_node_signature.assert_not_called()
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_not_called()
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_FAILED)
    mock_confirm_transfer_task.delay.assert_not_called()


@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch.object(
    TransferInteractor,
    '_TransferInteractor__sufficient_secondary_node_signatures',
    return_value=True)
@unittest.mock.patch.object(TransferInteractor,
                            '_TransferInteractor__add_primary_node_signature')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.confirm_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'primary'
                     }})
def test_submit_transfer_onchain_transfer_to_error(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_database_access, mock_confirm_transfer_task,
        mock_add_primary_node_signature,
        mock_sufficient_secondary_node_signatures, is_reversal_transfer,
        transfer_interactor, internal_transfer_id, cross_chain_transfer,
        validator_nonce, destination_hub_address,
        destination_forwarder_address, validator_node_signatures):
    mock_get_blockchain_config.return_value = {
        'hub': destination_hub_address,
        'forwarder': destination_forwarder_address
    }
    mock_get_blockchain_client().start_transfer_to_submission.side_effect = \
        Exception
    mock_database_access.read_validator_nonce_by_internal_transfer_id.\
        return_value = validator_nonce
    mock_database_access.read_validator_node_signatures.return_value = \
        validator_node_signatures
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
                internal_transfer_id, cross_chain_transfer, validator_nonce,
                validator_node_signatures))
    mock_database_access.create_validator_node_signature.assert_not_called()
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
