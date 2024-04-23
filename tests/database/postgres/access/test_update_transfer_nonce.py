import unittest.mock

import pytest
import sqlalchemy
import sqlalchemy.exc
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.access import update_transfer_nonce
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.models import Transfer
from tests.database.utilities import modify_model_instance


@pytest.mark.parametrize('transfer_status', [
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED
])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_empty_database_correct(
        mock_get_session, database_session_maker, transfer_status,
        initialized_database_session, transfer):
    mock_get_session.return_value = database_session_maker
    destination_blockchain = Blockchain(transfer.destination_blockchain_id)
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, [destination_blockchain],
        [transfer_status], [None])
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[0])).one_or_none()[0]
    assert transfer.nonce is None
    update_transfer_nonce(transfer.id, destination_blockchain, 0)
    initialized_database_session.refresh(transfer)
    assert transfer.nonce == 0


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.ETHEREUM, Blockchain.BNB_CHAIN, Blockchain.AVALANCHE
], [
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED
], [None, 2, 0, 1, 3, 7, 4, 6, 5])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_with_failed_nonces_created_first(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    minimum_failed_nonce_transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.nonce == 2)).one_or_none()[0]
    update_transfer_nonce(internal_transfer_ids[0], Blockchain.ETHEREUM, 100)
    initialized_database_session.refresh(minimum_failed_nonce_transfer)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[0])).one_or_none()[0]
    assert minimum_failed_nonce_transfer.nonce is None
    assert transfer.nonce == 2


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.ETHEREUM, Blockchain.BNB_CHAIN, Blockchain.AVALANCHE
], [
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED
], [2, 0, 1, 3, None, 7, 4, 6, 5])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_with_failed_nonces_created_in_the_middle(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    minimum_failed_nonce_transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.nonce == 2)).one_or_none()[0]
    update_transfer_nonce(internal_transfer_ids[4], Blockchain.ETHEREUM, 100)
    initialized_database_session.refresh(minimum_failed_nonce_transfer)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[4])).one_or_none()[0]
    assert minimum_failed_nonce_transfer.nonce is None
    assert transfer.nonce == 2


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.AVALANCHE, Blockchain.ETHEREUM
], [
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED
], [0, 1, None, None, None])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_failed_transfers_with_empty_nonces(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    update_transfer_nonce(internal_transfer_ids[4], Blockchain.ETHEREUM, 2)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[4])).one_or_none()[0]
    assert transfer.nonce == 2


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.BNB_CHAIN, Blockchain.AVALANCHE, Blockchain.ETHEREUM
], [
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED
], [2, 0, 1, 3, 7, 4, 6, 5, None])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_with_failed_nonces_created_last(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    minimum_failed_nonce_transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.nonce == 2)).one_or_none()[0]
    update_transfer_nonce(internal_transfer_ids[8], Blockchain.ETHEREUM, 100)
    initialized_database_session.refresh(minimum_failed_nonce_transfer)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[8])).one_or_none()[0]
    assert minimum_failed_nonce_transfer.nonce is None
    assert transfer.nonce == 2


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.AVALANCHE, Blockchain.ETHEREUM
], [
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED
], [0, 1, 2, 3, None])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_with_success_nonces_greater_nonce_received(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    update_transfer_nonce(internal_transfer_ids[4], Blockchain.ETHEREUM, 100)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[4])).one_or_none()[0]
    assert transfer.nonce == 100


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.AVALANCHE, Blockchain.ETHEREUM
], [
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED
], [0, 1, 2, 3, None])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_with_success_nonces_smaller_nonce_received(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    update_transfer_nonce(internal_transfer_ids[4], Blockchain.ETHEREUM, 1)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[4])).one_or_none()[0]
    assert transfer.nonce == 1


@pytest.mark.parametrize(('destination_blockchains', 'statuses', 'nonces'), [([
    Blockchain.ETHEREUM, Blockchain.ETHEREUM, Blockchain.ETHEREUM,
    Blockchain.AVALANCHE, Blockchain.ETHEREUM
], [
    TransferStatus.DESTINATION_TRANSACTION_CONFIRMED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED,
    TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED,
    TransferStatus.DESTINATION_TRANSACTION_FAILED
], [0, 1, 2, 3, None])])
@unittest.mock.patch('pantos.validatornode.database.access.get_session_maker')
def test_update_transfer_nonce_with_success_nonces_equal_nonce_received(
        mock_get_session, database_session_maker, initialized_database_session,
        transfer, destination_blockchains, statuses, nonces):
    mock_get_session.return_value = database_session_maker
    internal_transfer_ids = _create_database_records(
        initialized_database_session, transfer, destination_blockchains,
        statuses, nonces)
    update_transfer_nonce(internal_transfer_ids[4], Blockchain.ETHEREUM, 3)
    transfer = initialized_database_session.execute(
        sqlalchemy.select(Transfer).filter(
            Transfer.id == internal_transfer_ids[4])).one_or_none()[0]
    assert transfer.nonce == 1


def _create_database_records(database_session, transfer,
                             destination_blockchains, statuses, nonces):
    internal_transfer_ids = []
    for i, (destination_blockchain, status,
            nonce) in enumerate(zip(destination_blockchains, statuses,
                                    nonces)):
        source_blockchain = list(Blockchain)[(destination_blockchain.value + 1)
                                             % len(Blockchain)]
        modified_transfer = modify_model_instance(
            transfer, source_blockchain_id=source_blockchain.value,
            destination_blockchain_id=destination_blockchain.value,
            validator_nonce=i, task_id=f'{i}', source_transfer_id=i,
            destination_transfer_id=i, source_transaction_id=f'{i}',
            destination_transaction_id=f'{i}', nonce=nonce,
            status_id=status.value)
        database_session.add(modified_transfer)
        database_session.flush()
        internal_transfer_ids.append(modified_transfer.id)
    database_session.commit()
    return internal_transfer_ids
