import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

from pantos.validatornode.database.access import read_validator_node_signature


@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_read_validator_node_signature_existent_correct(
        mock_get_session, database_session_maker, initialized_database_session,
        validator_node_signature):
    mock_get_session.side_effect = database_session_maker
    initialized_database_session.add(validator_node_signature)
    initialized_database_session.commit()
    internal_transfer_id = validator_node_signature.transfer.id
    validator_node = validator_node_signature.validator_node
    destination_blockchain = Blockchain(
        validator_node.forwarder_contract.blockchain_id)
    destination_forwarder_address = BlockchainAddress(
        validator_node.forwarder_contract.address)
    validator_node_address = BlockchainAddress(validator_node.address)
    signature = read_validator_node_signature(internal_transfer_id,
                                              destination_blockchain,
                                              destination_forwarder_address,
                                              validator_node_address)
    assert signature == validator_node_signature.signature


@pytest.mark.parametrize('validator_node_existent', [True, False])
@pytest.mark.parametrize('transfer_existent', [True, False])
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_read_validator_node_signature_nonexistent_correct(
        mock_get_session, database_session_maker, transfer_existent,
        validator_node_existent, initialized_database_session, transfer,
        validator_node):
    mock_get_session.side_effect = database_session_maker
    if transfer_existent:
        initialized_database_session.add(transfer)
    if validator_node_existent:
        initialized_database_session.add(validator_node)
    initialized_database_session.commit()
    internal_transfer_id = transfer.id if transfer_existent else 83672
    destination_blockchain = Blockchain(
        validator_node.forwarder_contract.blockchain_id)
    destination_forwarder_address = BlockchainAddress(
        validator_node.forwarder_contract.address)
    validator_node_address = BlockchainAddress(validator_node.address)
    signature = read_validator_node_signature(internal_transfer_id,
                                              destination_blockchain,
                                              destination_forwarder_address,
                                              validator_node_address)
    assert signature is None
