import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.access import TransferToDataResponse
from pantos.validatornode.database.access import read_transfer_to_data


@pytest.mark.parametrize('number_transfers', [0, 1, 2])
@unittest.mock.patch('pantos.validatornode.database.access.get_session')
def test_read_transfer_to_data_correct(
        mock_get_session, database_session_maker, number_transfers,
        initialized_database_session, source_token_contract,
        destination_token_contract, transfer, other_source_token_contract,
        other_destination_token_contract, other_transfer):
    mock_get_session.side_effect = database_session_maker
    if number_transfers > 0:
        initialized_database_session.add(source_token_contract)
        initialized_database_session.add(destination_token_contract)
        initialized_database_session.add(transfer)
        if number_transfers > 1:
            initialized_database_session.add(other_source_token_contract)
            initialized_database_session.add(other_destination_token_contract)
            initialized_database_session.add(other_transfer)
        initialized_database_session.commit()

    result = read_transfer_to_data(Blockchain(transfer.source_blockchain_id),
                                   transfer.source_transaction_id)

    if number_transfers == 0:
        assert result is None
    else:
        assert isinstance(result, TransferToDataResponse)
        assert result.internal_transfer_id == transfer.id
        assert result.destination_blockchain is Blockchain(
            transfer.destination_blockchain_id)
        assert result.source_transfer_id == transfer.source_transfer_id
        assert result.sender_address == transfer.sender_address
        assert result.recipient_address == transfer.recipient_address
        assert result.source_token_address == source_token_contract.address
        assert (result.destination_token_address ==
                destination_token_contract.address)
        assert result.amount == transfer.amount
        assert result.validator_nonce == transfer.validator_nonce
