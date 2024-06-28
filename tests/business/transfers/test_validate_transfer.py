import dataclasses
import unittest.mock

import celery.exceptions  # type: ignore
import pytest
from pantos.common.entities import TransactionStatus

from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.business.transfers import validate_transfer_task
from pantos.validatornode.database.enums import TransferStatus


@pytest.mark.parametrize('token_decimals_correct', [True, False])
@pytest.mark.parametrize('external_token_address_correct', [True, False])
@pytest.mark.parametrize('destination_token_active', [True, False])
@pytest.mark.parametrize('recipient_address_valid', [True, False])
@pytest.mark.parametrize('in_other_source_transaction', [True, False])
@pytest.mark.parametrize('is_primary_node', [True, False])
@unittest.mock.patch('pantos.validatornode.business.transfers.'
                     'submit_transfer_to_primary_node_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.business.base.config')
def test_validate_transfer_confirmed_correct(
        mock_config, mock_get_blockchain_client, mock_database_access,
        mock_submit_transfer_onchain_task,
        mock_submit_transfer_to_primary_node_task, is_primary_node,
        in_other_source_transaction, recipient_address_valid,
        destination_token_active, external_token_address_correct,
        token_decimals_correct, transfer_interactor, internal_transfer_id,
        cross_chain_transfer):
    mock_config_dict = {
        'application': {
            'mode': 'primary' if is_primary_node else 'secondary'
        }
    }
    mock_config.__getitem__.side_effect = mock_config_dict.__getitem__
    transfer_in_source_transaction = (
        cross_chain_transfer
        if not in_other_source_transaction else dataclasses.replace(
            cross_chain_transfer,
            source_transfer_id=cross_chain_transfer.source_transfer_id + 1))
    _initialize_mock_blockchain_client(
        mock_get_blockchain_client, TransactionStatus.CONFIRMED,
        transfer_in_source_transaction, recipient_address_valid, True,
        destination_token_active, external_token_address_correct,
        token_decimals_correct)

    validation_completed = transfer_interactor.validate_transfer(
        internal_transfer_id, cross_chain_transfer)

    assert validation_completed
    is_reversal_transfer = (not recipient_address_valid
                            or not destination_token_active
                            or not external_token_address_correct
                            or not token_decimals_correct)
    transfer_in_source_transaction.is_reversal_transfer = is_reversal_transfer
    if not is_reversal_transfer:
        mock_database_access.update_reversal_transfer.assert_not_called()
    else:
        mock_database_access.update_reversal_transfer.assert_called_once_with(
            internal_transfer_id,
            cross_chain_transfer.eventual_destination_blockchain,
            cross_chain_transfer.eventual_recipient_address,
            cross_chain_transfer.eventual_destination_token_address)
    mock_database_access.update_transfer_status.assert_not_called()
    if is_primary_node:
        mock_submit_transfer_onchain_task.delay.assert_called_once_with(
            internal_transfer_id, transfer_in_source_transaction.to_dict())
        mock_submit_transfer_to_primary_node_task.delay.assert_not_called()
    else:
        mock_submit_transfer_onchain_task.delay.assert_not_called()
        mock_submit_transfer_to_primary_node_task.delay.\
            assert_called_once_with(internal_transfer_id,
                                    transfer_in_source_transaction.to_dict())


@unittest.mock.patch('pantos.validatornode.business.transfers.'
                     'submit_transfer_to_primary_node_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_validate_transfer_unconfirmed_correct(
        mock_get_blockchain_client, mock_database_access,
        mock_submit_transfer_onchain_task,
        mock_submit_transfer_to_primary_node_task, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    _initialize_mock_blockchain_client(mock_get_blockchain_client,
                                       TransactionStatus.UNCONFIRMED,
                                       cross_chain_transfer, True, True, True,
                                       True, True)

    validation_completed = transfer_interactor.validate_transfer(
        internal_transfer_id, cross_chain_transfer)

    assert not validation_completed
    mock_database_access.update_reversal_transfer.assert_not_called()
    mock_database_access.update_transfer_status.assert_not_called()
    mock_submit_transfer_onchain_task.delay.assert_not_called()
    mock_submit_transfer_to_primary_node_task.delay.assert_not_called()


@unittest.mock.patch('pantos.validatornode.business.transfers.'
                     'submit_transfer_to_primary_node_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_validate_transfer_reverted_correct(
        mock_get_blockchain_client, mock_database_access,
        mock_submit_transfer_onchain_task,
        mock_submit_transfer_to_primary_node_task, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    _initialize_mock_blockchain_client(mock_get_blockchain_client,
                                       TransactionStatus.REVERTED,
                                       cross_chain_transfer, True, True, True,
                                       True, True)

    validation_completed = transfer_interactor.validate_transfer(
        internal_transfer_id, cross_chain_transfer)

    assert validation_completed
    mock_database_access.update_reversal_transfer.assert_not_called()
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_TRANSACTION_REVERTED)
    mock_submit_transfer_onchain_task.delay.assert_not_called()
    mock_submit_transfer_to_primary_node_task.delay.assert_not_called()


@unittest.mock.patch('pantos.validatornode.business.transfers.'
                     'submit_transfer_to_primary_node_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_validate_transfer_invalid_correct(
        mock_get_blockchain_client, mock_database_access,
        mock_submit_transfer_onchain_task,
        mock_submit_transfer_to_primary_node_task, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    _initialize_mock_blockchain_client(mock_get_blockchain_client,
                                       TransactionStatus.CONFIRMED,
                                       cross_chain_transfer, True, False, True,
                                       True, True)

    validation_completed = transfer_interactor.validate_transfer(
        internal_transfer_id, cross_chain_transfer)

    assert validation_completed
    mock_database_access.update_reversal_transfer.assert_not_called()
    mock_database_access.update_transfer_status.assert_called_once_with(
        internal_transfer_id, TransferStatus.SOURCE_TRANSACTION_INVALID)
    mock_submit_transfer_onchain_task.delay.assert_not_called()
    mock_submit_transfer_to_primary_node_task.delay.assert_not_called()


@unittest.mock.patch('pantos.validatornode.business.transfers.'
                     'submit_transfer_to_primary_node_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_validate_transfer_not_found_in_transaction_error(
        mock_get_blockchain_client, mock_database_access,
        mock_submit_transfer_onchain_task,
        mock_submit_transfer_to_primary_node_task, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    _initialize_mock_blockchain_client(mock_get_blockchain_client,
                                       TransactionStatus.CONFIRMED, None, True,
                                       True, True, True, True)

    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.validate_transfer(internal_transfer_id,
                                              cross_chain_transfer)

    assert (exception_info.value.details['internal_transfer_id'] ==
            internal_transfer_id)
    assert (exception_info.value.details['transfer'] == cross_chain_transfer)
    mock_database_access.update_reversal_transfer.assert_not_called()
    mock_database_access.update_transfer_status.assert_not_called()
    mock_submit_transfer_onchain_task.delay.assert_not_called()
    mock_submit_transfer_to_primary_node_task.delay.assert_not_called()


@unittest.mock.patch('pantos.validatornode.business.transfers.'
                     'submit_transfer_to_primary_node_task')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.submit_transfer_onchain_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
def test_validate_transfer_other_error(
        mock_get_blockchain_client, mock_database_access,
        mock_submit_transfer_onchain_task,
        mock_submit_transfer_to_primary_node_task, transfer_interactor,
        internal_transfer_id, cross_chain_transfer):
    mock_get_blockchain_client.side_effect = Exception

    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.validate_transfer(internal_transfer_id,
                                              cross_chain_transfer)

    assert (exception_info.value.details['internal_transfer_id'] ==
            internal_transfer_id)
    assert (exception_info.value.details['transfer'] == cross_chain_transfer)
    mock_database_access.update_reversal_transfer.assert_not_called()
    mock_database_access.update_transfer_status.assert_not_called()
    mock_submit_transfer_onchain_task.delay.assert_not_called()
    mock_submit_transfer_to_primary_node_task.delay.assert_not_called()


@pytest.mark.parametrize('validation_completed', [True, False])
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config',
    {'tasks': {
        'validate_transfer': {
            'retry_interval_in_seconds': 120
        }
    }})
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_validate_transfer_task_correct(mock_transfer_interactor,
                                        validation_completed,
                                        internal_transfer_id,
                                        cross_chain_transfer,
                                        cross_chain_transfer_dict):
    mock_transfer_interactor().validate_transfer.return_value = \
        validation_completed
    if validation_completed:
        validate_transfer_task(internal_transfer_id, cross_chain_transfer_dict)
    else:
        with pytest.raises(celery.exceptions.Retry):
            validate_transfer_task(internal_transfer_id,
                                   cross_chain_transfer_dict)
    mock_transfer_interactor().validate_transfer.assert_called_once_with(
        internal_transfer_id, cross_chain_transfer)


@unittest.mock.patch('pantos.validatornode.business.transfers.config', {
    'tasks': {
        'validate_transfer': {
            'retry_interval_after_error_in_seconds': 300
        }
    }
})
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_validate_transfer_task_error(mock_transfer_interactor,
                                      internal_transfer_id,
                                      cross_chain_transfer,
                                      cross_chain_transfer_dict):
    mock_transfer_interactor().validate_transfer.side_effect = \
        TransferInteractorError('')
    with pytest.raises(TransferInteractorError):
        validate_transfer_task(internal_transfer_id, cross_chain_transfer_dict)
    mock_transfer_interactor().validate_transfer.assert_called_once_with(
        internal_transfer_id, cross_chain_transfer)


def _initialize_mock_blockchain_client(
        mock_get_blockchain_client, transaction_status,
        transfer_in_source_transaction, recipient_address_valid,
        source_token_active, destination_token_active,
        external_token_address_correct, token_decimals_correct):
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_utilities = mock_blockchain_client.get_utilities()
    mock_blockchain_utilities.read_transaction_status.return_value = \
        transaction_status
    mock_blockchain_client.read_outgoing_transfers_in_transaction.\
        return_value = (
            [] if transfer_in_source_transaction is None else
            [transfer_in_source_transaction])
    mock_blockchain_client.is_valid_recipient_address.return_value = \
        recipient_address_valid
    mock_blockchain_client.is_token_active.side_effect = [
        source_token_active, destination_token_active
    ]
    if external_token_address_correct:
        mock_blockchain_client.read_external_token_address.side_effect = (
            lambda x0, blockchain: transfer_in_source_transaction.
            source_token_address
            if blockchain is transfer_in_source_transaction.source_blockchain
            else transfer_in_source_transaction.destination_token_address)
    else:
        mock_blockchain_client.read_external_token_address.return_value = \
            'some_wrong_address'
    if token_decimals_correct:
        mock_blockchain_client.read_token_decimals.return_value = 18
    else:
        mock_blockchain_client.read_token_decimals.side_effect = (
            lambda token_address: 8 if token_address ==
            transfer_in_source_transaction.source_token_address else 18)
    mock_blockchain_client.is_equal_address = lambda address_one, \
        address_two: address_one.lower() == address_two.lower()
