import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.blockchains.solana import SolanaClient
from pantos.validatornode.blockchains.solana import SolanaClientError


@pytest.fixture(scope='module')
@unittest.mock.patch.object(SolanaClient, '__init__', lambda self: None)
def solana_client():
    return SolanaClient()


def test_get_blockchain_correct(solana_client):
    assert solana_client.get_blockchain() is Blockchain.SOLANA
    assert SolanaClient.get_blockchain() is Blockchain.SOLANA


def test_get_error_class_correct(solana_client):
    assert solana_client.get_error_class() is SolanaClientError
    assert SolanaClient.get_error_class() is SolanaClientError


def test_is_equal_address_not_implemented(solana_client):
    with pytest.raises(NotImplementedError):
        solana_client.is_equal_address('address_one', 'address_two')
