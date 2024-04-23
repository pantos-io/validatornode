import pytest
from pantos.common.blockchains.enums import Blockchain

_INTERNAL_TRANSFER_ID = 92068

_SOURCE_BLOCKCHAIN = list(Blockchain)[0]

_DESTINATION_BLOCKCHAIN = list(Blockchain)[-1]

_SOURCE_TRANSACTION_ID = \
    '0xd9102630aaed1372a8dd546a7ea47bf519b8cc0a28044b9ce91041cdaf736c2b'

_SOURCE_TRANSFER_ID = 251275

_SENDER_ADDRESS = '0x5c77e49Ff409B78a13e8260B95c5cF80719eF46A'

_RECIPIENT_ADDRESS = '0x52c303919766e8063DEFB775eE96ca9ff1dE4fA5'

_SOURCE_TOKEN_ADDRESS = '0xabd53da7ed2d182F48Fb835363107868306098b1'

_DESTINATION_TOKEN_ADDRESS = '0x8AB7AaE817572f649a0E0019320136fFfD5B0892'

_AMOUNT = 4588 * 10**18

_VALIDATOR_NONCE = 254029629735728


@pytest.fixture
def internal_transfer_id():
    return _INTERNAL_TRANSFER_ID


@pytest.fixture
def source_blockchain():
    return _SOURCE_BLOCKCHAIN


@pytest.fixture
def destination_blockchain():
    return _DESTINATION_BLOCKCHAIN


@pytest.fixture
def source_transaction_id():
    return _SOURCE_TRANSACTION_ID


@pytest.fixture
def source_transfer_id():
    return _SOURCE_TRANSFER_ID


@pytest.fixture
def sender_address():
    return _SENDER_ADDRESS


@pytest.fixture
def recipient_address():
    return _RECIPIENT_ADDRESS


@pytest.fixture
def source_token_address():
    return _SOURCE_TOKEN_ADDRESS


@pytest.fixture
def destination_token_address():
    return _DESTINATION_TOKEN_ADDRESS


@pytest.fixture
def amount():
    return _AMOUNT


@pytest.fixture
def validator_nonce():
    return _VALIDATOR_NONCE
