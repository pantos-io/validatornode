"""Module for Solana-specific clients and errors.

"""
import uuid

from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.entities import CrossChainTransfer


class SolanaClientError(BlockchainClientError):
    """Exception class for all Solana client errors.

    """
    pass


class SolanaClient(BlockchainClient):
    """Solana-specific blockchain client.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.SOLANA

    @classmethod
    def get_error_class(cls) -> type[BlockchainClientError]:
        # Docstring inherited
        return SolanaClientError

    def get_own_address(self) -> BlockchainAddress:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def is_token_active(self, token_address: BlockchainAddress) -> bool:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def is_valid_recipient_address(self, recipient_address: str) -> bool:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def is_valid_transaction_id(self, transaction_id: str) -> bool:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def is_valid_validator_nonce(self, nonce: int) -> bool:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def is_equal_address(self, address_one: str, address_two: str) -> bool:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def read_external_token_address(
            self, token_address: BlockchainAddress,
            external_blockchain: Blockchain) -> BlockchainAddress | None:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def read_minimum_validator_node_signatures(self) -> int:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def read_outgoing_transfers_from_block(self, from_block_number: int) -> \
            BlockchainClient.ReadOutgoingTransfersFromBlockResponse:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def read_outgoing_transfers_in_transaction(
            self, transaction_id: str,
            hub_address: BlockchainAddress) -> list[CrossChainTransfer]:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def read_token_decimals(self, token_address: BlockchainAddress) -> int:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def read_validator_node_addresses(self) -> list[BlockchainAddress]:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def recover_transfer_to_signer_address(
            self,
            request: BlockchainClient.TransferToSignerAddressRecoveryRequest) \
            -> BlockchainAddress:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def sign_transfer_to_message(
            self,
            request: BlockchainClient.TransferToMessageSignRequest) -> str:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def start_transfer_to_submission(
            self, request: BlockchainClient.TransferToSubmissionStartRequest) \
            -> uuid.UUID:
        # Docstring inherited
        raise NotImplementedError  # pragma: no cover

    def _read_transfer_to_transaction_data(
            self, transaction_id: str, read_destination_transfer_id: bool) \
            -> BlockchainClient._TransferToTransactionDataResponse:
        raise NotImplementedError  # pragma: no cover
