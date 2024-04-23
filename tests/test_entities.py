import dataclasses

import pytest
import web3
from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

from pantos.validatornode.entities import CrossChainTransfer


def _to_blockchain_address(integer):
    hex_string = hex(integer)[2:]
    blockchain_address = (web3.constants.ADDRESS_ZERO[:-len(hex_string)] +
                          hex_string)
    return BlockchainAddress(web3.Web3.to_checksum_address(blockchain_address))


_SOURCE_BLOCKCHAIN = Blockchain.ETHEREUM

_DESTINATION_BLOCKCHAIN = Blockchain.AVALANCHE

_SOURCE_HUB_ADDRESS = _to_blockchain_address(1)

_SOURCE_TRANSFER_ID = 10**4

_SOURCE_TRANSACTION_ID = 'some_transaction_id'

_SOURCE_BLOCK_NUMBER = 10**6

_SOURCE_BLOCK_HASH = 'some_block_hash'

_SENDER_ADDRESS = _to_blockchain_address(2)

_RECIPIENT_ADDRESS = _to_blockchain_address(3)

_SOURCE_TOKEN_ADDRESS = _to_blockchain_address(4)

_DESTINATION_TOKEN_ADDRESS = _to_blockchain_address(5)

_AMOUNT = 10**18

_FEE = 10**17

_SERVICE_NODE_ADDRESS = _to_blockchain_address(6)


@pytest.fixture(scope='module', params=[True, False])
def cross_chain_transfer(request):
    return CrossChainTransfer(
        _SOURCE_BLOCKCHAIN, _DESTINATION_BLOCKCHAIN, _SOURCE_HUB_ADDRESS,
        _SOURCE_TRANSFER_ID, _SOURCE_TRANSACTION_ID, _SOURCE_BLOCK_NUMBER,
        _SOURCE_BLOCK_HASH, _SENDER_ADDRESS, _RECIPIENT_ADDRESS,
        _SOURCE_TOKEN_ADDRESS, _DESTINATION_TOKEN_ADDRESS, _AMOUNT, _FEE,
        _SERVICE_NODE_ADDRESS, is_reversal_transfer=request.param)


@pytest.fixture
def cross_chain_transfer_dict(cross_chain_transfer):
    return {
        'source_blockchain_id': _SOURCE_BLOCKCHAIN.value,
        'destination_blockchain_id': _DESTINATION_BLOCKCHAIN.value,
        'source_hub_address': _SOURCE_HUB_ADDRESS,
        'source_transfer_id': _SOURCE_TRANSFER_ID,
        'source_transaction_id': _SOURCE_TRANSACTION_ID,
        'source_block_number': _SOURCE_BLOCK_NUMBER,
        'source_block_hash': _SOURCE_BLOCK_HASH,
        'sender_address': _SENDER_ADDRESS,
        'recipient_address': _RECIPIENT_ADDRESS,
        'source_token_address': _SOURCE_TOKEN_ADDRESS,
        'destination_token_address': _DESTINATION_TOKEN_ADDRESS,
        'amount': _AMOUNT,
        'fee': _FEE,
        'service_node_address': _SERVICE_NODE_ADDRESS,
        'is_reversal_transfer': cross_chain_transfer.is_reversal_transfer
    }


def test_cross_chain_transfer_to_dict_correct(cross_chain_transfer,
                                              cross_chain_transfer_dict):
    assert cross_chain_transfer.to_dict() == cross_chain_transfer_dict


def test_cross_chain_transfer_from_dict_correct(cross_chain_transfer_dict,
                                                cross_chain_transfer):
    cross_chain_transfer_from_dict = CrossChainTransfer.from_dict(
        cross_chain_transfer_dict)
    assert cross_chain_transfer_from_dict == cross_chain_transfer
    if cross_chain_transfer.is_reversal_transfer:
        assert (cross_chain_transfer_from_dict.eventual_destination_blockchain
                == cross_chain_transfer.source_blockchain)
        assert (cross_chain_transfer_from_dict.eventual_recipient_address ==
                cross_chain_transfer.sender_address)
        assert (
            cross_chain_transfer_from_dict.eventual_destination_token_address
            == cross_chain_transfer.source_token_address)
    else:
        assert (cross_chain_transfer_from_dict.eventual_destination_blockchain
                == cross_chain_transfer.destination_blockchain)
        assert (cross_chain_transfer_from_dict.eventual_recipient_address ==
                cross_chain_transfer.recipient_address)
        assert (
            cross_chain_transfer_from_dict.eventual_destination_token_address
            == cross_chain_transfer.destination_token_address)


@pytest.mark.parametrize('removed_dict_key',
                         range(len(dataclasses.fields(CrossChainTransfer))))
def test_cross_chain_transfer_from_dict_key_error(removed_dict_key,
                                                  cross_chain_transfer_dict):
    del cross_chain_transfer_dict[list(cross_chain_transfer_dict)
                                  [removed_dict_key]]
    with pytest.raises(KeyError):
        CrossChainTransfer.from_dict(cross_chain_transfer_dict)
