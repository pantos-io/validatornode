"""Module for Fantom-specific clients and errors. Since Fantom is
Ethereum-compatible, the client implementation inherits from the
pantos.validatornode.blockchains.ethereum module.

"""
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.blockchains.ethereum import EthereumClient
from pantos.validatornode.blockchains.ethereum import EthereumClientError


class FantomClientError(EthereumClientError):
    """Exception class for all Fantom client errors.

    """
    pass


class FantomClient(EthereumClient):
    """Fantom-specific blockchain client.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.FANTOM

    @classmethod
    def get_error_class(cls) -> type[BlockchainClientError]:
        # Docstring inherited
        return FantomClientError
