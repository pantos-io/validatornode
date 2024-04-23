import unittest.mock

import pytest

from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.business.base import DuplicateSignatureError
from pantos.validatornode.business.base import InvalidSignatureError
from pantos.validatornode.business.base import InvalidSignerError
from pantos.validatornode.business.base import UnknownTransferError
from pantos.validatornode.business.signatures import SignatureInteractor
from pantos.validatornode.business.signatures import SignatureInteractorError
from pantos.validatornode.database.access import TransferToDataResponse

_FORWARDER_ADDRESS = '0x8960647eC8CAd5fEBc919b255C9F739f17D91e8B'

_SIGNER_ADDRESS = '0x977E8f4ee5d2c6DF05941A5e3A54A808f87edDE4'

_VALIDATOR_NODE_ADDRESSES_WITHOUT_SIGNER = [
    '0x6308bBEA49dB0AE3461C87545857216b2F5Ce992',
    '0x7C17b7A1B2128F97522b31Ada5fEeF26ff9dE38c',
    '0xA7CD6BE13D729f371064b3eC933a4015D4B85Daa'
]

_VALIDATOR_NODE_ADDRESSES_WITH_SIGNER = \
    _VALIDATOR_NODE_ADDRESSES_WITHOUT_SIGNER + [_SIGNER_ADDRESS]


@pytest.fixture
def secondary_node_signature_add_request(source_blockchain,
                                         source_transaction_id, signature):
    return SignatureInteractor.SecondaryNodeSignatureAddRequest(
        source_blockchain=source_blockchain,
        source_transaction_id=source_transaction_id, signature=signature)


@pytest.fixture
def transfer_to_data_response(internal_transfer_id, destination_blockchain,
                              source_transfer_id, sender_address,
                              recipient_address, source_token_address,
                              destination_token_address, amount,
                              validator_nonce):
    return TransferToDataResponse(
        internal_transfer_id=internal_transfer_id,
        destination_blockchain=destination_blockchain,
        source_transfer_id=source_transfer_id, sender_address=sender_address,
        recipient_address=recipient_address,
        source_token_address=source_token_address,
        destination_token_address=destination_token_address, amount=amount,
        validator_nonce=validator_nonce)


@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_config',
    return_value={'forwarder': _FORWARDER_ADDRESS})
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.database_access')
def test_add_secondary_node_signature_correct(
        mock_database_access, mock_get_blockchain_client,
        mock_get_blockchain_config, transfer_to_data_response,
        secondary_node_signature_add_request, signature_interactor):
    mock_database_access.read_transfer_to_data.return_value = \
        transfer_to_data_response
    mock_database_access.read_validator_node_signature.return_value = None
    mock_get_blockchain_client().read_validator_node_addresses.return_value = \
        _VALIDATOR_NODE_ADDRESSES_WITH_SIGNER
    mock_get_blockchain_client().recover_transfer_to_signer_address.\
        return_value = _SIGNER_ADDRESS

    signature_interactor.add_secondary_node_signature(
        secondary_node_signature_add_request)

    mock_database_access.create_validator_node_signature.\
        assert_called_once_with(
            transfer_to_data_response.internal_transfer_id,
            transfer_to_data_response.destination_blockchain,
            _FORWARDER_ADDRESS, _SIGNER_ADDRESS,
            secondary_node_signature_add_request.signature)


@unittest.mock.patch(
    'pantos.validatornode.business.signatures.database_access')
def test_add_secondary_node_signature_unknown_transfer_error(
        mock_database_access, secondary_node_signature_add_request,
        signature_interactor):
    mock_database_access.read_transfer_to_data.return_value = None

    with pytest.raises(UnknownTransferError) as exception_info:
        signature_interactor.add_secondary_node_signature(
            secondary_node_signature_add_request)

    assert isinstance(exception_info.value, SignatureInteractorError)
    assert not isinstance(exception_info.value, DuplicateSignatureError)
    assert not isinstance(exception_info.value, InvalidSignatureError)
    assert not isinstance(exception_info.value, InvalidSignerError)


@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_config',
    return_value={'forwarder': _FORWARDER_ADDRESS})
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.database_access')
def test_add_secondary_node_signature_invalid_signature_error(
        mock_database_access, mock_get_blockchain_client,
        mock_get_blockchain_config, transfer_to_data_response,
        secondary_node_signature_add_request, signature_interactor):
    mock_database_access.read_transfer_to_data.return_value = \
        transfer_to_data_response
    mock_get_blockchain_client().recover_transfer_to_signer_address.\
        side_effect = BlockchainClientError('')

    with pytest.raises(InvalidSignatureError) as exception_info:
        signature_interactor.add_secondary_node_signature(
            secondary_node_signature_add_request)

    assert isinstance(exception_info.value, SignatureInteractorError)
    assert not isinstance(exception_info.value, DuplicateSignatureError)
    assert not isinstance(exception_info.value, InvalidSignerError)
    assert not isinstance(exception_info.value, UnknownTransferError)


@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_config',
    return_value={'forwarder': _FORWARDER_ADDRESS})
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.database_access')
def test_add_secondary_node_signature_duplicate_signature_error(
        mock_database_access, mock_get_blockchain_client,
        mock_get_blockchain_config, transfer_to_data_response,
        secondary_node_signature_add_request, signature_interactor):
    mock_database_access.read_transfer_to_data.return_value = \
        transfer_to_data_response
    mock_database_access.read_validator_node_signature.return_value = \
        secondary_node_signature_add_request.signature
    mock_get_blockchain_client().recover_transfer_to_signer_address.\
        return_value = _SIGNER_ADDRESS

    with pytest.raises(DuplicateSignatureError) as exception_info:
        signature_interactor.add_secondary_node_signature(
            secondary_node_signature_add_request)

    assert isinstance(exception_info.value, SignatureInteractorError)
    assert not isinstance(exception_info.value, InvalidSignatureError)
    assert not isinstance(exception_info.value, InvalidSignerError)
    assert not isinstance(exception_info.value, UnknownTransferError)


@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_config',
    return_value={'forwarder': _FORWARDER_ADDRESS})
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.signatures.database_access')
def test_add_secondary_node_signature_invalid_signer_error(
        mock_database_access, mock_get_blockchain_client,
        mock_get_blockchain_config, transfer_to_data_response,
        secondary_node_signature_add_request, signature_interactor):
    mock_database_access.read_transfer_to_data.return_value = \
        transfer_to_data_response
    mock_database_access.read_validator_node_signature.return_value = None
    mock_get_blockchain_client().read_validator_node_addresses.return_value = \
        _VALIDATOR_NODE_ADDRESSES_WITHOUT_SIGNER
    mock_get_blockchain_client().recover_transfer_to_signer_address.\
        return_value = _SIGNER_ADDRESS

    with pytest.raises(InvalidSignerError) as exception_info:
        signature_interactor.add_secondary_node_signature(
            secondary_node_signature_add_request)

    assert isinstance(exception_info.value, SignatureInteractorError)
    assert not isinstance(exception_info.value, DuplicateSignatureError)
    assert not isinstance(exception_info.value, InvalidSignatureError)
    assert not isinstance(exception_info.value, UnknownTransferError)


@unittest.mock.patch(
    'pantos.validatornode.business.signatures.database_access')
def test_add_secondary_node_signature_database_error(
        mock_database_access, secondary_node_signature_add_request,
        signature_interactor):
    mock_database_access.read_transfer_to_data.side_effect = Exception

    with pytest.raises(SignatureInteractorError) as exception_info:
        signature_interactor.add_secondary_node_signature(
            secondary_node_signature_add_request)

    assert not isinstance(exception_info.value, DuplicateSignatureError)
    assert not isinstance(exception_info.value, InvalidSignatureError)
    assert not isinstance(exception_info.value, InvalidSignerError)
    assert not isinstance(exception_info.value, UnknownTransferError)
