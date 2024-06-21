import unittest.mock

import pytest
import requests
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.restclient import _TRANSFER_SIGNATURE_RESOURCE
from pantos.validatornode.restclient import _VALIDATOR_NONCE_RESOURCE
from pantos.validatornode.restclient import PrimaryNodeClient
from pantos.validatornode.restclient import PrimaryNodeClientError
from pantos.validatornode.restclient import PrimaryNodeDuplicateSignatureError
from pantos.validatornode.restclient import PrimaryNodeInvalidSignatureError
from pantos.validatornode.restclient import PrimaryNodeInvalidSignerError
from pantos.validatornode.restclient import PrimaryNodeUnknownTransferError

_PRIMARY_NODE_URL = 'https://some.url'

_SOURCE_BLOCKCHAIN = list(Blockchain)[0]

_SOURCE_TRANSACTION_ID = ('0xd9102630aaed1372a8dd546a7ea47bf519b8cc0a28044b9ce'
                          '91041cdaf736c2b')

_SIGNATURE = ('0x89f4bb92379a5f1ab97a8dcf01c73d1eb6d25e173fa17286fa5ed2416e369'
              '67a3e68f634f808e74c1f018cfd55264c9ce961772fcbda4bba627603f7c196'
              '1aa11b')

_VALIDATOR_NONCE = 9565957430447361915976742018


@pytest.fixture
def primary_node_client():
    return PrimaryNodeClient(_PRIMARY_NODE_URL)


@pytest.fixture
def validator_nonce_get_request():
    return PrimaryNodeClient.ValidatorNonceGetRequest(
        source_blockchain=_SOURCE_BLOCKCHAIN,
        source_transaction_id=_SOURCE_TRANSACTION_ID)


@pytest.fixture
def transfer_signature_post_request():
    return PrimaryNodeClient.TransferSignaturePostRequest(
        source_blockchain=_SOURCE_BLOCKCHAIN,
        source_transaction_id=_SOURCE_TRANSACTION_ID, signature=_SIGNATURE)


@pytest.mark.parametrize('with_trailing_slash', [True, False])
def test_init_correct(with_trailing_slash):
    assert not _PRIMARY_NODE_URL.endswith('/')
    url_with_trailing_slash = _PRIMARY_NODE_URL + '/'
    client = PrimaryNodeClient(
        url_with_trailing_slash if with_trailing_slash else _PRIMARY_NODE_URL)
    assert (
        client._PrimaryNodeClient__primary_node_url == url_with_trailing_slash)


@unittest.mock.patch('pantos.validatornode.restclient.requests.get')
def test_get_validator_nonce_correct(mock_requests_get, primary_node_client,
                                     validator_nonce_get_request):
    mock_requests_get().status_code = requests.codes.ok
    mock_requests_get().json.return_value = {
        'validator_nonce': _VALIDATOR_NONCE
    }
    mock_requests_get.call_count = 0

    validator_nonce = primary_node_client.get_validator_nonce(
        validator_nonce_get_request)

    _assert_requests_get_call_correct(mock_requests_get, primary_node_client)
    assert validator_nonce == _VALIDATOR_NONCE


@pytest.mark.parametrize('send_error',
                         [requests.Timeout, requests.RequestException])
@unittest.mock.patch('pantos.validatornode.restclient.requests.get')
def test_get_validator_nonce_send_error(mock_requests_get, send_error,
                                        primary_node_client,
                                        validator_nonce_get_request):
    mock_requests_get.side_effect = send_error

    with pytest.raises(PrimaryNodeClientError) as exception_info:
        primary_node_client.get_validator_nonce(validator_nonce_get_request)

    _assert_requests_get_call_correct(mock_requests_get, primary_node_client)
    assert isinstance(exception_info.value.__context__, send_error)


@unittest.mock.patch('pantos.validatornode.restclient.requests.get')
def test_get_validator_nonce_decode_error(mock_requests_get,
                                          primary_node_client,
                                          validator_nonce_get_request):
    mock_requests_get().json.side_effect = requests.JSONDecodeError('', '', 0)
    mock_requests_get.call_count = 0

    with pytest.raises(PrimaryNodeClientError) as exception_info:
        primary_node_client.get_validator_nonce(validator_nonce_get_request)

    _assert_requests_get_call_correct(mock_requests_get, primary_node_client)
    assert isinstance(exception_info.value.__context__,
                      requests.JSONDecodeError)


@pytest.mark.parametrize(
    'primary_node_error',
    [(requests.codes.bad_request, 'Some validation error.',
      PrimaryNodeClientError),
     (requests.codes.not_found, 'Unknown transfer.',
      PrimaryNodeUnknownTransferError),
     (requests.codes.internal_server_error, None, PrimaryNodeClientError)])
@unittest.mock.patch('pantos.validatornode.restclient.requests.get')
def test_get_validator_nonce_primary_node_error(mock_requests_get,
                                                primary_node_error,
                                                primary_node_client,
                                                validator_nonce_get_request):
    mock_requests_get().status_code = primary_node_error[0]
    mock_requests_get().json.return_value = {'message': primary_node_error[1]}
    mock_requests_get.call_count = 0

    with pytest.raises(primary_node_error[2]) as exception_info:
        primary_node_client.get_validator_nonce(validator_nonce_get_request)

    _assert_requests_get_call_correct(mock_requests_get, primary_node_client)
    assert exception_info.value.details['status_code'] == primary_node_error[0]
    assert (exception_info.value.details.get('response_message') ==
            primary_node_error[1])


@unittest.mock.patch('pantos.validatornode.restclient.requests.post')
def test_post_transfer_signature_correct(mock_requests_post,
                                         primary_node_client,
                                         transfer_signature_post_request):
    mock_requests_post().status_code = requests.codes.no_content
    mock_requests_post.call_count = 0

    primary_node_client.post_transfer_signature(
        transfer_signature_post_request)

    _assert_requests_post_call_correct(mock_requests_post, primary_node_client)


@pytest.mark.parametrize('send_error',
                         [requests.Timeout, requests.RequestException])
@unittest.mock.patch('pantos.validatornode.restclient.requests.post')
def test_post_transfer_signature_send_error(mock_requests_post, send_error,
                                            primary_node_client,
                                            transfer_signature_post_request):
    mock_requests_post.side_effect = send_error

    with pytest.raises(PrimaryNodeClientError) as exception_info:
        primary_node_client.post_transfer_signature(
            transfer_signature_post_request)

    _assert_requests_post_call_correct(mock_requests_post, primary_node_client)
    assert isinstance(exception_info.value.__context__, send_error)


@unittest.mock.patch('pantos.validatornode.restclient.requests.post')
def test_post_transfer_signature_decode_error(mock_requests_post,
                                              primary_node_client,
                                              transfer_signature_post_request):
    mock_requests_post().json.side_effect = requests.JSONDecodeError('', '', 0)
    mock_requests_post.call_count = 0

    with pytest.raises(PrimaryNodeClientError) as exception_info:
        primary_node_client.post_transfer_signature(
            transfer_signature_post_request)

    _assert_requests_post_call_correct(mock_requests_post, primary_node_client)
    assert isinstance(exception_info.value.__context__,
                      requests.JSONDecodeError)


@pytest.mark.parametrize(
    'primary_node_error',
    [(requests.codes.bad_request, 'Some validation error.',
      PrimaryNodeClientError),
     (requests.codes.conflict, 'Duplicate signature.',
      PrimaryNodeDuplicateSignatureError),
     (requests.codes.bad_request, 'Invalid signature.',
      PrimaryNodeInvalidSignatureError),
     (requests.codes.forbidden, 'Invalid signer.',
      PrimaryNodeInvalidSignerError),
     (requests.codes.not_found, 'Unknown transfer.',
      PrimaryNodeUnknownTransferError),
     (requests.codes.internal_server_error, None, PrimaryNodeClientError)])
@unittest.mock.patch('pantos.validatornode.restclient.requests.post')
def test_post_transfer_signature_primary_node_error(
        mock_requests_post, primary_node_error, primary_node_client,
        transfer_signature_post_request):
    mock_requests_post().status_code = primary_node_error[0]
    mock_requests_post().json.return_value = {'message': primary_node_error[1]}
    mock_requests_post.call_count = 0

    with pytest.raises(primary_node_error[2]) as exception_info:
        primary_node_client.post_transfer_signature(
            transfer_signature_post_request)

    _assert_requests_post_call_correct(mock_requests_post, primary_node_client)
    assert exception_info.value.details['status_code'] == primary_node_error[0]
    assert (exception_info.value.details.get('response_message') ==
            primary_node_error[1])


def _assert_requests_get_call_correct(mock_requests_get, primary_node_client):
    mock_requests_get.assert_called_once_with(
        f'{_PRIMARY_NODE_URL}/{_VALIDATOR_NONCE_RESOURCE}?'
        f'source_blockchain_id={_SOURCE_BLOCKCHAIN.value}&'
        f'source_transaction_id={_SOURCE_TRANSACTION_ID}',
        timeout=primary_node_client._PrimaryNodeClient__timeout)


def _assert_requests_post_call_correct(mock_requests_post,
                                       primary_node_client):
    mock_requests_post.assert_called_once_with(
        f'{_PRIMARY_NODE_URL}/{_TRANSFER_SIGNATURE_RESOURCE}', json={
            'source_blockchain_id': _SOURCE_BLOCKCHAIN.value,
            'source_transaction_id': _SOURCE_TRANSACTION_ID,
            'signature': _SIGNATURE
        }, timeout=primary_node_client._PrimaryNodeClient__timeout)
