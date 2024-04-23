import itertools
import unittest.mock
import uuid

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.business.transfers import TransferInteractorError
from pantos.validatornode.entities import CrossChainTransfer

_SOURCE_BLOCKCHAIN = list(Blockchain)[0]

_DESTINATION_BLOCKCHAINS = [
    blockchain for blockchain in Blockchain
    if blockchain is not _SOURCE_BLOCKCHAIN
]

_FROM_BLOCK = [0, 229003]

_CONFIRMATIONS = [14, 200]

_LAST_BLOCK_NUMBERS = [228766, 5417158]

_VALIDATOR_NONCE = 386180924573188711


@pytest.mark.parametrize('transfers_already_known', [True, False])
@pytest.mark.parametrize('number_transfers', [31, 443, 3816])
@pytest.mark.parametrize('number_blocks', [-1, 0, 1, 87, 988, 6143])
@pytest.mark.parametrize('last_block_number', _LAST_BLOCK_NUMBERS)
@pytest.mark.parametrize('confirmations', _CONFIRMATIONS)
@pytest.mark.parametrize('from_block', _FROM_BLOCK)
@unittest.mock.patch('pantos.validatornode.business.transfers.random')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.validate_transfer_task')
@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
def test_detect_new_transfers_correct(
        mock_get_blockchain_config, mock_get_blockchain_client,
        mock_database_access, mock_validate_transfer_task, mock_random,
        from_block, confirmations, last_block_number, number_blocks,
        number_transfers, transfers_already_known, transfer_interactor):
    mock_get_blockchain_config.return_value = _get_blockchain_config(
        from_block, confirmations)
    outgoing_transfers_response = _get_outgoing_transfers_from_block_response(
        from_block, confirmations, last_block_number, number_blocks,
        number_transfers)
    number_transfers = len(outgoing_transfers_response.outgoing_transfers)
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_client.is_valid_validator_nonce.side_effect = \
        itertools.cycle([False, True])
    mock_blockchain_client.read_outgoing_transfers_from_block.return_value = \
        outgoing_transfers_response
    mock_database_access.read_blockchain_last_block_number.return_value = \
        last_block_number
    mock_database_access.read_transfer_id.side_effect = (
        lambda x0, test_transfer_id: int(test_transfer_id)
        if transfers_already_known else None)
    mock_database_access.create_transfer.side_effect = (
        lambda request: request.source_transfer_id)
    mock_validate_transfer_task.delay().id = str(uuid.uuid4())
    mock_random.getrandbits.return_value = _VALIDATOR_NONCE

    transfer_interactor.detect_new_transfers(_SOURCE_BLOCKCHAIN)

    if transfers_already_known or number_transfers == 0:
        mock_database_access.create_transfer.assert_not_called()
        mock_database_access.update_transfer_task_id.assert_not_called()
        mock_validate_transfer_task.assert_not_called()
    else:
        assert (mock_database_access.create_transfer.call_count ==
                number_transfers)
        assert (mock_database_access.update_transfer_task_id.call_count ==
                number_transfers)
        validate_transfer_task_calls = []
        for transfer in outgoing_transfers_response.outgoing_transfers:
            validate_transfer_task_calls.append(
                unittest.mock.call(transfer.source_transfer_id,
                                   transfer.to_dict()))
        mock_validate_transfer_task.delay.assert_has_calls(
            validate_transfer_task_calls, any_order=True)

    if number_transfers == 0:
        mock_database_access.update_blockchain_last_block_number.\
            assert_not_called()
    else:
        mock_database_access.update_blockchain_last_block_number.\
            assert_called_once_with(
                _SOURCE_BLOCKCHAIN,
                outgoing_transfers_response.to_block_number)


@unittest.mock.patch('pantos.validatornode.business.transfers.database_access')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
def test_detect_new_transfers_block_number_error(mock_get_blockchain_config,
                                                 mock_get_blockchain_client,
                                                 mock_database_access,
                                                 transfer_interactor):
    mock_get_blockchain_config.return_value = _get_blockchain_config(
        _FROM_BLOCK[0], _CONFIRMATIONS[0])
    outgoing_transfers_response = _get_outgoing_transfers_from_block_response(
        _FROM_BLOCK[0], _CONFIRMATIONS[0], _LAST_BLOCK_NUMBERS[0], -1000, 0)
    mock_blockchain_client = mock_get_blockchain_client()
    mock_blockchain_client.read_outgoing_transfers_from_block.return_value = \
        outgoing_transfers_response
    mock_database_access.read_blockchain_last_block_number.return_value = \
        _LAST_BLOCK_NUMBERS[0]
    with pytest.raises(TransferInteractorError):
        transfer_interactor.detect_new_transfers(_SOURCE_BLOCKCHAIN)


@unittest.mock.patch('pantos.validatornode.business.transfers.database_access',
                     side_effect=Exception)
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_client')
@unittest.mock.patch(
    'pantos.validatornode.business.transfers.get_blockchain_config')
def test_detect_new_transfers_other_error(mock_get_blockchain_config,
                                          mock_get_blockchain_client,
                                          mock_database_access,
                                          transfer_interactor):
    with pytest.raises(TransferInteractorError) as exception_info:
        transfer_interactor.detect_new_transfers(_SOURCE_BLOCKCHAIN)
    assert (exception_info.value.details['source_blockchain']
            is _SOURCE_BLOCKCHAIN)


def _get_blockchain_config(from_block, confirmations):
    return {'from_block': from_block, 'confirmations': confirmations}


def _get_outgoing_transfers_from_block_response(from_block, confirmations,
                                                last_block_number,
                                                number_blocks,
                                                number_transfers):
    from_block_number = max(last_block_number - confirmations, from_block)
    to_block_number = from_block_number + number_blocks
    outgoing_transfers = []
    if from_block_number <= to_block_number:
        for test_transfer_id in range(1, number_transfers + 1):
            destination_blockchain = _DESTINATION_BLOCKCHAINS[
                test_transfer_id % len(_DESTINATION_BLOCKCHAINS)]
            cross_chain_transfer = CrossChainTransfer(
                source_blockchain=_SOURCE_BLOCKCHAIN,
                destination_blockchain=destination_blockchain,
                source_hub_address=str(test_transfer_id),
                source_transfer_id=test_transfer_id,
                source_transaction_id=str(test_transfer_id),
                source_block_number=test_transfer_id,
                source_block_hash=str(test_transfer_id),
                sender_address=str(test_transfer_id),
                recipient_address=str(test_transfer_id),
                source_token_address=str(test_transfer_id),
                destination_token_address=str(test_transfer_id),
                amount=test_transfer_id, fee=test_transfer_id,
                service_node_address=str(test_transfer_id))
            outgoing_transfers.append(cross_chain_transfer)
    return BlockchainClient.ReadOutgoingTransfersFromBlockResponse(
        outgoing_transfers=outgoing_transfers, to_block_number=to_block_number)
