import json
import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.business.base import DuplicateSignatureError
from pantos.validatornode.business.base import InvalidSignatureError
from pantos.validatornode.business.base import InvalidSignerError
from pantos.validatornode.business.base import UnknownTransferError

_RESTFUL_RESOURCE = '/transfersignature'

_SIGNATURE = ('0x89f4bb92379a5f1ab97a8dcf01c73d1eb6d25e173fa17286fa5ed2416e369'
              '67a3e68f634f808e74c1f018cfd55264c9ce961772fcbda4bba627603f7c196'
              '1aa11b')


@pytest.fixture
def signature():
    return _SIGNATURE


@pytest.fixture
def transfer_signature_request(source_blockchain, source_transaction_id,
                               signature):
    return {
        'source_blockchain_id': source_blockchain.value,
        'source_transaction_id': source_transaction_id,
        'signature': signature
    }


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.SignatureInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_transfer_signature_correct(mock_get_blockchain_config,
                                    mock_get_blockchain_client,
                                    mock_signature_interactor,
                                    transfer_signature_request, test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

    mock_signature_interactor().\
        add_secondary_node_signature.assert_called_once()
    assert response.status_code == 204
    assert len(response.text) == 0


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
def test_transfer_signature_bad_request_schema_error(
        mock_get_blockchain_config, mock_get_blockchain_client,
        source_blockchain_id, source_transaction_id,
        transfer_signature_request, test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = False
    transfer_signature_request['source_blockchain_id'] = source_blockchain_id
    transfer_signature_request['source_transaction_id'] = source_transaction_id

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

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
@unittest.mock.patch('pantos.validatornode.restapi.SignatureInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_transfer_signature_bad_request_signature_error(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_signature_interactor, transfer_signature_request, test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_signature_interactor().add_secondary_node_signature.side_effect = \
        InvalidSignatureError

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

    assert response.status_code == 400
    assert json.loads(response.text)['message'] == 'Invalid signature.'


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.SignatureInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_transfer_signature_forbidden_signature_error(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_signature_interactor, transfer_signature_request, test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_signature_interactor().add_secondary_node_signature.side_effect = \
        DuplicateSignatureError

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

    assert response.status_code == 403
    assert json.loads(response.text)['message'] == 'Duplicate signature.'


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.SignatureInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_transfer_signature_forbidden_signer_error(mock_get_blockchain_config,
                                                   mock_get_blockchain_client,
                                                   mock_signature_interactor,
                                                   transfer_signature_request,
                                                   test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_signature_interactor().add_secondary_node_signature.side_effect = \
        InvalidSignerError

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

    assert response.status_code == 403
    assert json.loads(response.text)['message'] == 'Invalid signer.'


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.SignatureInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_transfer_signature_not_found_error(mock_get_blockchain_config,
                                            mock_get_blockchain_client,
                                            mock_signature_interactor,
                                            transfer_signature_request,
                                            test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_signature_interactor().add_secondary_node_signature.side_effect = \
        UnknownTransferError

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

    assert response.status_code == 404
    assert json.loads(response.text)['message'] == 'Unknown transfer.'


@pytest.mark.filterwarnings(
    'ignore:The \'__version__\' attribute is deprecated')
@unittest.mock.patch('pantos.validatornode.restapi.SignatureInteractor')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_client')
@unittest.mock.patch('pantos.validatornode.restapi.get_blockchain_config',
                     return_value={'active': True})
def test_transfer_signature_internal_server_error(mock_get_blockchain_config,
                                                  mock_get_blockchain_client,
                                                  mock_signature_interactor,
                                                  transfer_signature_request,
                                                  test_client):
    mock_get_blockchain_client().is_valid_transaction_id.return_value = True
    mock_signature_interactor().add_secondary_node_signature.side_effect = \
        Exception

    response = test_client.post(_RESTFUL_RESOURCE,
                                json=transfer_signature_request)

    assert response.status_code == 500
