import datetime
import unittest.mock

import pytest
import sqlalchemy
from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

from pantos.validatornode.database.access import \
    create_validator_node_signature
from pantos.validatornode.database.models import ValidatorNodeSignature


@pytest.mark.parametrize('validator_node_existent', [True, False])
@pytest.mark.parametrize('forwarder_contract_existent', [True, False])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_create_validator_node_signature_correct(
        mock_get_session, database_session_maker, forwarder_contract_existent,
        validator_node_existent, initialized_database_session, transfer,
        destination_forwarder_contract, validator_node, signatures):
    mock_get_session.return_value = database_session_maker
    initialized_database_session.add(transfer)
    if forwarder_contract_existent:
        initialized_database_session.add(destination_forwarder_contract)
    if validator_node_existent:
        initialized_database_session.add(validator_node)
    initialized_database_session.commit()
    signature = signatures[0]
    create_validator_node_signature(
        transfer.id, Blockchain(destination_forwarder_contract.blockchain_id),
        BlockchainAddress(destination_forwarder_contract.address),
        BlockchainAddress(validator_node.address), signature)
    validator_node_signature = initialized_database_session.execute(
        sqlalchemy.select(ValidatorNodeSignature)).one()[0]
    assert validator_node_signature.transfer_id == transfer.id
    if validator_node_existent:
        assert validator_node_signature.validator_node_id == validator_node.id
    assert validator_node_signature.signature == signature
    assert validator_node_signature.created < datetime.datetime.now(
        datetime.timezone.utc).replace(tzinfo=None)
