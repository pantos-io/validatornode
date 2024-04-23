import unittest.mock

import pytest

from pantos.validatornode.database.access import read_validator_node_signatures
from pantos.validatornode.database.models import ValidatorNode
from pantos.validatornode.database.models import ValidatorNodeSignature


@pytest.mark.parametrize('other_signatures', [True, False])
@pytest.mark.parametrize('number_signatures', [0, 1, 2, 3])
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_read_validator_node_signatures_correct(
        mock_get_session, database_session_maker, number_signatures,
        other_signatures, initialized_database_session, transfer,
        other_transfer, destination_forwarder_contract,
        other_destination_forwarder_contract, validator_node_addresses,
        signatures):
    mock_get_session.side_effect = database_session_maker
    initialized_database_session.add(destination_forwarder_contract)
    initialized_database_session.add(transfer)
    for i in range(number_signatures):
        validator_node = ValidatorNode(
            forwarder_contract=destination_forwarder_contract,
            address=validator_node_addresses[i])
        initialized_database_session.add(validator_node)
        validator_node_signature = ValidatorNodeSignature(
            transfer=transfer, validator_node=validator_node,
            signature=signatures[i])
        initialized_database_session.add(validator_node_signature)
    if other_signatures:
        initialized_database_session.add(other_destination_forwarder_contract)
        initialized_database_session.add(other_transfer)
        for validator_node_address, signature in zip(validator_node_addresses,
                                                     signatures):
            validator_node = ValidatorNode(
                forwarder_contract=other_destination_forwarder_contract,
                address=validator_node_address)
            initialized_database_session.add(validator_node)
            validator_node_signature = ValidatorNodeSignature(
                transfer=other_transfer, validator_node=validator_node,
                signature=signature[:-1])
            initialized_database_session.add(validator_node_signature)
    initialized_database_session.commit()
    results = read_validator_node_signatures(transfer.id)
    assert len(results) == number_signatures
    for i, result in enumerate(results):
        assert result[0] == validator_node_addresses[i]
        assert result[1] == signatures[i]
