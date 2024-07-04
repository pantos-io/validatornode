import unittest.mock

import celery.exceptions  # type: ignore
import pytest

from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.business.transfers import \
    submit_transfer_to_primary_node_task
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.restclient import PrimaryNodeClient
from pantos.validatornode.restclient import PrimaryNodeClientError
from pantos.validatornode.restclient import PrimaryNodeDuplicateSignatureError

_TASK_INTERVAL = 120


@pytest.mark.parametrize('signature_in_database', [True, False])
@pytest.mark.parametrize('duplicate_signature', [True, False])
@pytest.mark.parametrize('is_reversal_transfer', [True, False])
@unittest.mock.patch.object(PrimaryNodeClient, 'post_transfer_signature')
@unittest.mock.patch.object(PrimaryNodeClient, 'get_validator_nonce')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
@unittest.mock.patch('pantos.validatornode.business.transfers.config',
                     {'application': {
                         'primary_url': 'https://some.url'
                     }})
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'secondary'
                     }})
def test_submit_transfer_to_primary_node_correct(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_database_access, mock_get_validator_nonce,
        mock_post_transfer_signature, is_reversal_transfer,
        duplicate_signature, signature_in_database, transfer_interactor,
        internal_transfer_id, cross_chain_transfer, validator_nonce,
        destination_hub_address, destination_forwarder_address,
        validator_node_signatures):
    mock_get_blockchain_config.return_value = {
        'hub': destination_hub_address,
        'forwarder': destination_forwarder_address
    }
    own_address = list(validator_node_signatures.keys())[0]
    signature = list(validator_node_signatures.values())[0]
    mock_get_blockchain_client().get_own_address.return_value = own_address
    mock_get_blockchain_client().sign_transfer_to_message.return_value = \
        signature
    mock_database_access.read_validator_node_signature.return_value = (
        signature if signature_in_database else None)
    mock_get_validator_nonce.return_value = validator_nonce
    if duplicate_signature:
        mock_post_transfer_signature.side_effect = \
            PrimaryNodeDuplicateSignatureError
    cross_chain_transfer.is_reversal_transfer = is_reversal_transfer

    submission_completed = transfer_interactor.submit_transfer_to_primary_node(
        internal_transfer_id, cross_chain_transfer)

    assert submission_completed
    mock_get_validator_nonce.assert_called_once_with(
        PrimaryNodeClient.ValidatorNonceGetRequest(
            cross_chain_transfer.source_blockchain,
            cross_chain_transfer.source_transaction_id))
    mock_post_transfer_signature.assert_called_once_with(
        PrimaryNodeClient.TransferSignaturePostRequest(
            cross_chain_transfer.source_blockchain,
            cross_chain_transfer.source_transaction_id, signature))
    if signature_in_database:
        mock_database_access.create_validator_node_signature.\
            assert_not_called()
    else:
        mock_database_access.create_validator_node_signature.\
            assert_called_once_with(
                internal_transfer_id,
                cross_chain_transfer.eventual_destination_blockchain,
                destination_forwarder_address, own_address, signature)
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_called_once_with(internal_transfer_id, destination_hub_address,
                                destination_forwarder_address)
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id,
        TransferStatus.SOURCE_REVERSAL_TRANSACTION_SUBMITTED
        if is_reversal_transfer else
        TransferStatus.DESTINATION_TRANSACTION_SUBMITTED)


@unittest.mock.patch.object(PrimaryNodeClient, 'post_transfer_signature')
@unittest.mock.patch.object(PrimaryNodeClient, 'get_validator_nonce')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch('pantos.validatornode.business.transfers.config',
                     {'application': {
                         'primary_url': 'https://some.url'
                     }})
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'secondary'
                     }})
def test_submit_transfer_to_primary_node_error(mock_database_access,
                                               mock_get_validator_nonce,
                                               mock_post_transfer_signature,
                                               transfer_interactor,
                                               internal_transfer_id,
                                               cross_chain_transfer):
    mock_get_validator_nonce.side_effect = PrimaryNodeClientError

    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.submit_transfer_to_primary_node(
            internal_transfer_id, cross_chain_transfer)

    assert (exception_info.value.details['internal_transfer_id'] ==
            internal_transfer_id)
    assert (exception_info.value.details['transfer'] == cross_chain_transfer)
    mock_post_transfer_signature.assert_not_called()
    mock_database_access.create_validator_node_signature.assert_not_called()
    mock_database_access.update_transfer_submitted_destination_transaction.\
        assert_not_called()
    mock_database_access.update_transfer_status.assert_not_called()


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config', {
        'tasks': {
            'submit_transfer_onchain': {
                'retry_interval_in_seconds': _TASK_INTERVAL
            },
        }
    })
@unittest.mock.patch('pantos.validatornode.business.base.config',
                     {'application': {
                         'mode': 'primary'
                     }})
def test_submit_transfer_to_primary_node_as_primary_node(
        mock_submit_transfer_onchain_task, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    mock_submit_transfer_onchain_task.__name__ = 'submit_transfer_onchain_task'

    submission_completed = transfer_interactor.submit_transfer_to_primary_node(
        internal_transfer_id, cross_chain_transfer)

    assert submission_completed
    mock_submit_transfer_onchain_task.apply_async.assert_called_once_with(
        args=(internal_transfer_id, cross_chain_transfer.to_dict()),
        countdown=_TASK_INTERVAL)


@pytest.mark.parametrize('submission_completed', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config', {
        'tasks': {
            'submit_transfer_to_primary_node': {
                'retry_interval_in_seconds': _TASK_INTERVAL
            }
        }
    })
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_submit_transfer_to_primary_node_task_correct(
        mock_transfer_interactor, submission_completed, internal_transfer_id,
        cross_chain_transfer, cross_chain_transfer_dict):
    mock_transfer_interactor().submit_transfer_to_primary_node.return_value = \
        submission_completed
    if submission_completed:
        submit_transfer_to_primary_node_task(internal_transfer_id,
                                             cross_chain_transfer_dict)
    else:
        with pytest.raises(celery.exceptions.Retry):
            submit_transfer_to_primary_node_task(internal_transfer_id,
                                                 cross_chain_transfer_dict)
    mock_transfer_interactor().submit_transfer_to_primary_node.\
        assert_called_once_with(internal_transfer_id, cross_chain_transfer)


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config', {
        'tasks': {
            'submit_transfer_to_primary_node': {
                'retry_interval_after_error_in_seconds': _TASK_INTERVAL
            }
        }
    })
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_submit_transfer_to_primary_node_task_error(mock_transfer_interactor,
                                                    internal_transfer_id,
                                                    cross_chain_transfer,
                                                    cross_chain_transfer_dict):
    mock_transfer_interactor().submit_transfer_to_primary_node.side_effect = \
        TransferInteractorError('')
    with pytest.raises(TransferInteractorError):
        submit_transfer_to_primary_node_task(internal_transfer_id,
                                             cross_chain_transfer_dict)
    mock_transfer_interactor().submit_transfer_to_primary_node.\
        assert_called_once_with(internal_transfer_id, cross_chain_transfer)
