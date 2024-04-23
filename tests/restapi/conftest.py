import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.restapi import flask_app

_SOURCE_BLOCKCHAIN = Blockchain.AVALANCHE

_SOURCE_TRANSACTION_ID = \
    '0x658eef360399805a882241eb8a0c04b4a725621c014984e62427d1f645ad74d1'

_VALIDATOR_NONCE = 2849384844385064953


@pytest.fixture
def test_client():
    with flask_app.test_client() as test_client:
        return test_client


@pytest.fixture
def source_blockchain():
    return _SOURCE_BLOCKCHAIN


@pytest.fixture
def source_transaction_id():
    return _SOURCE_TRANSACTION_ID


@pytest.fixture
def validator_nonce():
    return _VALIDATOR_NONCE
