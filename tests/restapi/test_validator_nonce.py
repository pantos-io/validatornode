import json
import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.business.base import UnknownTransferError


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.TransferInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_validator_nonce_correct(mock_get_blockchain_config,
                                 mock_get_blockchain_client,
                                 mock_transfer_interactor, source_blockchain,
                                 source_transaction_id, validator_nonce,
                                 test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_transfer_interactor().get_validator_nonce.return_value = \
        validator_nonce
    request_url = _get_request_url(source_blockchain.value,
                                   source_transaction_id)

    response = test_client.get(request_url)

    assert response.status_code == 200
    assert json.loads(response.text)['validator_nonce'] == validator_nonce


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@pytest.mark.parametrize('source_transaction_id', [None, 'some_string'])
@pytest.mark.parametrize(
    'source_blockchain_id',
    [None, 'some_string', Blockchain.ETHEREUM.value,
     max(Blockchain) + 1])
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_validator_nonce_bad_request_error(mock_get_blockchain_config,
                                           mock_get_blockchain_client,
                                           source_blockchain_id,
                                           source_transaction_id, test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = False
    request_url = _get_request_url(source_blockchain_id, source_transaction_id)

    response = test_client.get(request_url)

    assert response.status_code == 400
    message = json.loads(response.text)['message']
    source_blockchain_id_in_message = source_blockchain_id not in [
        blockchain.value for blockchain in Blockchain
    ]
    source_transaction_id_in_message = (source_transaction_id is None
                                        or not source_blockchain_id_in_message)
    assert (('source_blockchain_id' in message)
            is source_blockchain_id_in_message)
    assert (('source_transaction_id' in message)
            is source_transaction_id_in_message)


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.TransferInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_validator_nonce_not_found_error(mock_get_blockchain_config,
                                         mock_get_blockchain_client,
                                         mock_transfer_interactor,
                                         source_blockchain,
                                         source_transaction_id, test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_transfer_interactor().get_validator_nonce.side_effect = \
        UnknownTransferError
    request_url = _get_request_url(source_blockchain.value,
                                   source_transaction_id)

    response = test_client.get(request_url)

    assert response.status_code == 404
    assert json.loads(response.text)['message'] == 'Unknown transfer.'


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.TransferInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_validator_nonce_internal_server_error(mock_get_blockchain_config,
                                               mock_get_blockchain_client,
                                               mock_transfer_interactor,
                                               source_blockchain,
                                               source_transaction_id,
                                               test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_transfer_interactor().get_validator_nonce.side_effect = Exception
    request_url = _get_request_url(source_blockchain.value,
                                   source_transaction_id)

    response = test_client.get(request_url)

    assert response.status_code == 500


def _get_request_url(source_blockchain_id, source_transaction_id):
    request_url = '/validatornonce'
    if source_blockchain_id is not None:
        request_url += f'?source_blockchain_id={source_blockchain_id}'
    if source_transaction_id is not None:
        request_url += '?' if source_blockchain_id is None else '&'
        request_url += f'source_transaction_id={source_transaction_id}'
    return request_url
