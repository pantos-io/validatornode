"""Module for Cronos-specific clients and errors. Since Cronos is
Ethereum-compatible, the client implementation inherits from the
pantos.validatornode.blockchains.ethereum module.

"""
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.blockchains.ethereum import EthereumClient
from pantos.validatornode.blockchains.ethereum import EthereumClientError


class CronosClientError(EthereumClientError):
    """Exception class for all Cronos client errors.

    """
    pass


class CronosClient(EthereumClient):
    """Cronos-specific blockchain client.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.CRONOS

    @classmethod
    def get_error_class(cls) -> type[BlockchainClientError]:
        # Docstring inherited
        return CronosClientError
