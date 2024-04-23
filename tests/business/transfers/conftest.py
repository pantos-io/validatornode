import pytest

from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.entities import CrossChainTransfer

_SOURCE_HUB_ADDRESS = '0x716d4D0Ced39fe39fC936420d43B1B07f914F821'

_SOURCE_BLOCK_NUMBER = 6939037

_SOURCE_BLOCK_HASH = \
    '0xf24737b4629727d54884389e666616a4f34f9fbff05963fed0de50e14f492422'

_FEE = 5 * 10**17

_SERVICE_NODE_ADDRESS = '0xBd0E2ce4B8E1E4F28fd7C246F48c853f0CE186C5'


@pytest.fixture
def cross_chain_transfer(source_blockchain, destination_blockchain,
                         source_transfer_id, source_transaction_id,
                         sender_address, recipient_address,
                         source_token_address, destination_token_address,
                         amount):
    return CrossChainTransfer(
        source_blockchain=source_blockchain,
        destination_blockchain=destination_blockchain,
        source_hub_address=_SOURCE_HUB_ADDRESS,
        source_transfer_id=source_transfer_id,
        source_transaction_id=source_transaction_id,
        source_block_number=_SOURCE_BLOCK_NUMBER,
        source_block_hash=_SOURCE_BLOCK_HASH, sender_address=sender_address,
        recipient_address=recipient_address,
        source_token_address=source_token_address,
        destination_token_address=destination_token_address, amount=amount,
        fee=_FEE, service_node_address=_SERVICE_NODE_ADDRESS)


@pytest.fixture
def cross_chain_transfer_dict(cross_chain_transfer):
    return cross_chain_transfer.to_dict()


@pytest.fixture
def transfer_interactor():
    return TransferInteractor()
