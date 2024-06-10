import unittest.mock

import pytest

from pantos.validatornode.database.access import \
    update_transfer_submitted_destination_transaction
from tests.database.utilities import modify_model_instance


@pytest.mark.parametrize('destination_forwarder_contract_existent',
                         [True, False])
@pytest.mark.parametrize('destination_hub_contract_existent', [True, False])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_update_transfer_submitted_destination_transaction_correct(
        mock_get_session, mock_get_session_maker,
        destination_hub_contract_existent,
        destination_forwarder_contract_existent,
        initialized_database_session_maker, transfer,
        other_destination_blockchain, other_destination_hub_contract,
        other_destination_forwarder_contract):
    initialized_database_session = initialized_database_session_maker()
    mock_get_session.return_value = initialized_database_session
    mock_get_session_maker.return_value = initialized_database_session_maker
    transfer = modify_model_instance(
        transfer, destination_blockchain_id=other_destination_blockchain.id,
        destination_hub_contract=None, destination_forwarder_contract=None)
    initialized_database_session.add(transfer)
    if destination_hub_contract_existent:
        initialized_database_session.add(other_destination_hub_contract)
    if destination_forwarder_contract_existent:
        initialized_database_session.add(other_destination_forwarder_contract)
    initialized_database_session.commit()
    update_transfer_submitted_destination_transaction(
        transfer.id, other_destination_hub_contract.address,
        other_destination_forwarder_contract.address)
    initialized_database_session.refresh(transfer)
    assert (transfer.destination_hub_contract.blockchain_id ==
            transfer.destination_blockchain_id)
    assert (transfer.destination_hub_contract.address ==
            other_destination_hub_contract.address)
    assert (transfer.destination_forwarder_contract.blockchain_id ==
            transfer.destination_blockchain_id)
    assert (transfer.destination_forwarder_contract.address ==
            other_destination_forwarder_contract.address)
