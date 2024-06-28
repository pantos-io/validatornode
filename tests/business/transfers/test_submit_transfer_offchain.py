import unittest.mock

import celery.exceptions  # type: ignore
import pytest

from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.business.transfers import \
    submit_transfer_offchain_task


@pytest.mark.parametrize('submission_completed', [True, False])
@unittest.mock.patch('pantos.validatornode.business.transfers.config', {
    'tasks': {
        'submit_transfer_offchain': {
            'retry_interval_in_seconds': 120
        }
    }
})
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_submit_transfer_offchain_task_correct(mock_transfer_interactor,
                                               submission_completed,
                                               internal_transfer_id,
                                               cross_chain_transfer,
                                               cross_chain_transfer_dict):
    mock_transfer_interactor().submit_transfer_offchain.return_value = \
        submission_completed
    if submission_completed:
        submit_transfer_offchain_task(internal_transfer_id,
                                      cross_chain_transfer_dict)
    else:
        with pytest.raises(celery.exceptions.Retry):
            submit_transfer_offchain_task(internal_transfer_id,
                                          cross_chain_transfer_dict)
    mock_transfer_interactor().submit_transfer_offchain.\
        assert_called_once_with(internal_transfer_id, cross_chain_transfer)


@unittest.mock.patch(
    'pantos.validatornode.business.transfers.config', {
        'tasks': {
            'submit_transfer_offchain': {
                'retry_interval_after_error_in_seconds': 300
            }
        }
    })
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.TransferInteractor')
def test_submit_transfer_offchain_task_error(mock_transfer_interactor,
                                             internal_transfer_id,
                                             cross_chain_transfer,
                                             cross_chain_transfer_dict):
    mock_transfer_interactor().submit_transfer_offchain.side_effect = \
        TransferInteractorError('')
    with pytest.raises(TransferInteractorError):
        submit_transfer_offchain_task(internal_transfer_id,
                                      cross_chain_transfer_dict)
    mock_transfer_interactor().submit_transfer_offchain.\
        assert_called_once_with(internal_transfer_id, cross_chain_transfer)
