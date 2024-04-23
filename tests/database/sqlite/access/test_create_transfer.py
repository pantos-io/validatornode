import datetime
import unittest.mock

import pytest
import sqlalchemy
import sqlalchemy.exc
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.access import TransferCreationRequest
from pantos.validatornode.database.access import create_transfer
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.exceptions import \
    ValidatorNonceNotUniqueError
from pantos.validatornode.database.models import \
    UNIQUE_VALIDATOR_NONCE_CONSTRAINT
from pantos.validatornode.database.models import Transfer


@pytest.mark.parametrize('source_hub_contract_existent', [True, False])
@pytest.mark.parametrize('destination_token_contract_existent', [True, False])
@pytest.mark.parametrize('source_token_contract_existent', [True, False])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_create_transfer_correct(
        mock_get_session_maker, database_session_maker,
        source_token_contract_existent, destination_token_contract_existent,
        source_hub_contract_existent, initialized_database_session, transfer,
        source_token_contract, destination_token_contract,
        source_hub_contract):
    mock_get_session_maker.return_value = database_session_maker
    if source_token_contract_existent:
        initialized_database_session.add(source_token_contract)
    if destination_token_contract_existent:
        initialized_database_session.add(destination_token_contract)
    if source_hub_contract_existent:
        initialized_database_session.add(source_hub_contract)
    initialized_database_session.commit()

    transfer_creation_request = TransferCreationRequest(
        Blockchain(transfer.source_blockchain_id),
        Blockchain(transfer.destination_blockchain_id),
        transfer.sender_address, transfer.recipient_address,
        transfer.source_token_contract.address,
        transfer.destination_token_contract.address, transfer.amount,
        transfer.validator_nonce, transfer.source_hub_contract.address,
        transfer.source_transfer_id, transfer.source_transaction_id,
        transfer.source_block_number)
    internal_transfer_id = create_transfer(transfer_creation_request)

    created_transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer)).one_or_none()[0]
    _check_created_transfer(created_transfer, transfer, internal_transfer_id)


@pytest.mark.parametrize('error', [
    (sqlalchemy.exc.IntegrityError(UNIQUE_VALIDATOR_NONCE_CONSTRAINT, None,
                                   Exception()), ValidatorNonceNotUniqueError),
    (sqlalchemy.exc.IntegrityError('', None,
                                   Exception()), sqlalchemy.exc.IntegrityError)
])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_create_transfer_error(mock_get_session_maker, error, transfer):
    mock_get_session_maker().begin().__enter__().execute.side_effect = error[0]

    transfer_creation_request = TransferCreationRequest(
        Blockchain(transfer.source_blockchain_id),
        Blockchain(transfer.destination_blockchain_id),
        transfer.sender_address, transfer.recipient_address,
        transfer.source_token_contract.address,
        transfer.destination_token_contract.address, transfer.amount,
        transfer.validator_nonce, transfer.source_hub_contract.address,
        transfer.source_transfer_id, transfer.source_transaction_id,
        transfer.source_block_number)
    with pytest.raises(error[1]):
        create_transfer(transfer_creation_request)


def _check_created_transfer(created_transfer, input_transfer,
                            internal_transfer_id):
    assert created_transfer.id == internal_transfer_id
    assert (created_transfer.source_blockchain_id ==
            input_transfer.source_blockchain_id)
    assert (created_transfer.source_blockchain.id ==
            input_transfer.source_blockchain_id)
    assert (created_transfer.source_blockchain.name == Blockchain(
        input_transfer.source_blockchain_id).name)
    assert (created_transfer.destination_blockchain_id ==
            input_transfer.destination_blockchain_id)
    assert (created_transfer.destination_blockchain.id ==
            input_transfer.destination_blockchain_id)
    assert (created_transfer.destination_blockchain.name == Blockchain(
        input_transfer.destination_blockchain_id).name)
    assert created_transfer.sender_address == input_transfer.sender_address
    assert (
        created_transfer.recipient_address == input_transfer.recipient_address)
    assert (created_transfer.source_token_contract.blockchain_id ==
            input_transfer.source_token_contract.blockchain_id)
    assert (created_transfer.source_token_contract.address ==
            input_transfer.source_token_contract.address)
    assert (created_transfer.destination_token_contract.blockchain_id ==
            input_transfer.destination_token_contract.blockchain_id)
    assert (created_transfer.destination_token_contract.address ==
            input_transfer.destination_token_contract.address)
    assert created_transfer.amount == input_transfer.amount
    assert created_transfer.validator_nonce == input_transfer.validator_nonce
    assert (created_transfer.source_hub_contract.blockchain_id ==
            input_transfer.source_hub_contract.blockchain_id)
    assert (created_transfer.source_hub_contract.address ==
            input_transfer.source_hub_contract.address)
    assert created_transfer.destination_hub_contract_id is None
    assert created_transfer.destination_hub_contract is None
    assert created_transfer.destination_forwarder_contract_id is None
    assert created_transfer.destination_forwarder_contract is None
    assert created_transfer.task_id is None
    assert (created_transfer.source_transfer_id ==
            input_transfer.source_transfer_id)
    assert created_transfer.destination_transfer_id is None
    assert (created_transfer.source_transaction_id ==
            input_transfer.source_transaction_id)
    assert created_transfer.destination_transaction_id is None
    assert (created_transfer.source_block_number ==
            input_transfer.source_block_number)
    assert created_transfer.destination_block_number is None
    assert created_transfer.nonce is None
    assert (created_transfer.status_id ==
            TransferStatus.SOURCE_TRANSACTION_DETECTED.value)
    assert (created_transfer.status.id ==
            TransferStatus.SOURCE_TRANSACTION_DETECTED.value)
    assert (created_transfer.status.name ==
            TransferStatus.SOURCE_TRANSACTION_DETECTED.name)
    assert created_transfer.created < datetime.datetime.utcnow()
    assert created_transfer.updated is None
