import pytest

from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.entities import CrossChainTransfer

_SOURCE_HUB_ADDRESS = '0x716d4D0Ced39fe39fC936420d43B1B07f914F821'

_SOURCE_BLOCK_NUMBER = 6939037

_SOURCE_BLOCK_HASH = \
    '0xf24737b4629727d54884389e666616a4f34f9fbff05963fed0de50e14f492422'

_FEE = 5 * 10**17

_SERVICE_NODE_ADDRESS = '0xBd0E2ce4B8E1E4F28fd7C246F48c853f0CE186C5'

_MINIMUM_VALIDATOR_NODE_SIGNATURES = 3

_VALIDATOR_NODE_ADDRESSES = [
    '0x20B50a828a042B3F01aCB022e0C8A07e817bc9f5',
    '0xC433E88Aa983b552D99Cc98982768f787dE11f18',
    '0x1BE63cf4226F24d5e5C7B64B3bCBf4ceB25aAE31',
    '0x65333C563e7ee024cfe8D171EEBa654D685E90E3'
]

_VALIDATOR_NODE_SIGNATURES = [
    '0xedc95ed3d9eae50b63b104d09b09e7f1c5dafac94cd4922d37123a2a24a09b7736e8088'
    '8e7db95cff4f091989769fc2c52bd918fa1d451cfd38b2b9d4fab977f1b',
    '0x707481611b0d814d762d9d2f13fb320a7e38207c2fac24cd6a196b1260f9880e1ed94f5'
    '02c3bbaf25878c720956b66aa76d6a1e3088aedd144c429d730f17ee81c',
    '0x0ebedff2ee7a275898337345a502c729acc5fe13dc859215f19a57b29c8b20476887e3a'
    '65595014e2d1510434bc80c66992d724acd87075ad6a46b462a0b596a1c',
    '0xb7eb2a9e1906cfbf24a824ec5ced0ad5672ac9824884555ca99fe35641c13d78441c3da'
    '6aacc8ec52bf40a8bf5ef07c68ea15f191be0d98dfcbe4cfb5cc22b401c'
]


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
def minimum_validator_node_signatures():
    return _MINIMUM_VALIDATOR_NODE_SIGNATURES


@pytest.fixture
def validator_node_signatures():
    return dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES))


@pytest.fixture
def transfer_interactor():
    return TransferInteractor()
