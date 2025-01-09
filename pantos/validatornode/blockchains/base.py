"""Base classes for all blockchain clients and errors.

"""
import abc
import dataclasses
import logging
import typing
import uuid

import semantic_version  # type: ignore
from pantos.common.blockchains.base import BlockchainHandler
from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.base import VersionedContractAbi
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.enums import ContractAbi
from pantos.common.blockchains.factory import get_blockchain_utilities
from pantos.common.blockchains.factory import initialize_blockchain_utilities
from pantos.common.entities import TransactionStatus
from pantos.common.exceptions import ErrorCreator
from pantos.common.types import BlockchainAddress

from pantos.validatornode.configuration import config
from pantos.validatornode.configuration import get_blockchain_config
from pantos.validatornode.entities import CrossChainTransfer
from pantos.validatornode.exceptions import ValidatorNodeError
from pantos.validatornode.protocol import is_supported_protocol_version

_logger = logging.getLogger(__name__)


class BlockchainClientError(ValidatorNodeError):
    """Exception class for all blockchain client errors.

    """
    pass


class NonMatchingForwarderError(BlockchainClientError):
    """Exception to be raised if the Pantos Forwarder of a transferred
    token does not match the Pantos Forwarder of the Pantos Hub on the
    destination blockchain.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('non-matching Forwarder', **kwargs)


class SourceTransferIdAlreadyUsedError(BlockchainClientError):
    """Exception to be raised if an incoming token transfer request is
    submitted with a source blockchain Pantos transfer ID that was
    already used before for another token transfer.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('source transfer ID already used', **kwargs)


class UnresolvableTransferToSubmissionError(BlockchainClientError):
    """Exception to be raised if there has been an unresolvable error
    during a transferTo submission.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('unresolvable transferTo submission error', **kwargs)


class BlockchainClient(BlockchainHandler, ErrorCreator[BlockchainClientError]):
    """Base class for all blockchain clients.

    Attributes
    ----------
    protocol_version : semantic_version.Version
        The version of the Pantos protocol that the blockchain client
        instance is compliant with.

    """
    def __init__(self):
        """Construct a blockchain client instance.

        Raises
        ------
        BlockchainClientError
            If the corresponding blockchain utilities cannot be
            initialized.

        """
        self.protocol_version: typing.Final[
            semantic_version.Version] = semantic_version.Version(
                config['protocol'])
        assert is_supported_protocol_version(self.protocol_version)
        blockchain_nodes_urls = self._get_config()['providers']
        fallback_blockchain_nodes_urls = self._get_config().get(
            'fallback_providers', [])
        average_block_time = self._get_config()['average_block_time']
        required_transaction_confirmations = \
            self._get_config()['confirmations']
        transaction_network_id = self._get_config().get('chain_id')
        private_key = self._get_config()['private_key']
        private_key_password = self._get_config()['private_key_password']
        try:
            initialize_blockchain_utilities(
                self.get_blockchain(), blockchain_nodes_urls,
                fallback_blockchain_nodes_urls, average_block_time,
                required_transaction_confirmations, transaction_network_id,
                default_private_key=(private_key, private_key_password),
                celery_tasks_enabled=True)
        except BlockchainUtilitiesError:
            raise self._create_error(
                f'unable to initialize the {self.get_blockchain_name()} '
                'utilities')

    def get_own_address(self) -> BlockchainAddress:
        """Get the validator node's own address on the blockchain.

        Returns
        -------
        BlockchainAddress
            The validator node's address.

        """
        pass  # pragma: no cover

    def get_utilities(self) -> BlockchainUtilities:
        """Get the blockchain utilities associated with the blockchain
        client.

        Returns
        -------
        BlockchainUtilities
            The blockchain utilities.

        """
        return get_blockchain_utilities(self.get_blockchain())

    def is_protocol_version_supported_by_forwarder_contract(self) -> bool:
        """Determine if the configured protocol version is supported by
        the configured Forwarder contract.

        Returns
        -------
        bool
            True if the Forwarder contract supports the protocol
            version.

        """
        return self.get_utilities().is_protocol_version_supported_by_contract(
            self._get_config()['forwarder'],
            self._versioned_pantos_forwarder_abi)  # pragma: no cover

    def is_protocol_version_supported_by_hub_contract(self) -> bool:
        """Determine if the configured protocol version is supported by
        the configured Hub contract.

        Returns
        -------
        bool
            True if the Hub contract supports the protocol version.

        """
        return self.get_utilities().is_protocol_version_supported_by_contract(
            self._get_config()['hub'],
            self._versioned_pantos_hub_abi)  # pragma: no cover

    @abc.abstractmethod
    def is_token_active(self, token_address: BlockchainAddress) -> bool:
        """Determine if a token is active.

        Parameters
        ----------
        token_address : BlockchainAddress
            The blockchain address of the token.

        Returns
        -------
        bool
            True if the token is active.

        Raises
        ------
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainClientError
            If it cannot be determined if the token is active.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_valid_recipient_address(self, recipient_address: str) -> bool:
        """Determine if an address string is a valid recipient address
        on the blockchain.

        Parameters
        ----------
        recipient_address : str
            The address string to check.

        Returns
        -------
        bool
            True if the given address string is a valid recipient
            address on the blockchain.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_valid_transaction_id(self, transaction_id: str) -> bool:
        """Determine if a string is a valid transaction ID/hash on the
        blockchain.

        Parameters
        ----------
        transaction_id : str
            The string to check.

        Returns
        -------
        bool
            True if the given string is a valid transaction ID/hash on
            the blockchain.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_valid_validator_nonce(self, nonce: int) -> bool:
        """Determine if a given nonce is a valid (i.e. not yet used)
        validator nonce on the blockchain.

        Parameters
        ----------
        nonce : int
            The nonce to check.

        Returns
        -------
        bool
            True if the given nonce is a valid validator nonce on the
            blockchain.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_equal_address(self, address_one: BlockchainAddress,
                         address_two: BlockchainAddress) -> bool:
        """Determine if two addresses are equal.

        Parameters
        ----------
        address_one : BlockchainAddress
            The first address.
        address_two : BlockchainAddress
            The second address.

        Returns
        -------
        bool
            True if the addresses are equal.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def read_external_token_address(
            self, token_address: BlockchainAddress,
            external_blockchain: Blockchain) -> BlockchainAddress | None:
        """Read the external blockchain address of a token that is
        registered at the Pantos Hub.

        Parameters
        ----------
        token_address : BlockchainAddress
            The native blockchain address of the token.
        external_blockchain : Blockchain
            The blockchain to read the external token address for.

        Returns
        -------
        BlockchainAddress or None
            The external blockchain address of the token, or None if
            none is registered.

        Raises
        ------
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainClientError
            If the external token address cannot be read.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def read_minimum_validator_node_signatures(self) -> int:
        """Read the minimum number of required Pantos validator node
        signatures for validating a cross-chain transfer.

        Returns
        -------
        int
            The minimum number of signatures.

        Raises
        ------
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainClientError
            If the minimum number of signatures cannot be read.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class ReadOutgoingTransfersFromBlockResponse:
        """Response data for reading the outgoing Pantos transfers from
        a starting block.

        Attributes
        ----------
        outgoing_transfers : list of CrossChainTransfer
            The transfer data of the outgoing transfers included in the
            specified blocks.
        to_block_number : int
            The number of the last block that has been considered.

        """
        outgoing_transfers: list[CrossChainTransfer]
        to_block_number: int

    @abc.abstractmethod
    def read_outgoing_transfers_from_block(self, from_block_number: int) -> \
            ReadOutgoingTransfersFromBlockResponse:
        """Read the outgoing Pantos transfers included in blocks
        starting from the specified block number.

        Parameters
        ----------
        from_block_number : int
            The number of the first block to be considered.

        Returns
        -------
        ReadOutgoingTransfersFromBlockResponse
            The outgoing transfers data.

        Raises
        ------
        BlockchainClientError
            If the outgoing transfers cannot be read.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def read_outgoing_transfers_in_transaction(
            self, transaction_id: str,
            hub_address: BlockchainAddress) -> list[CrossChainTransfer]:
        """Read the outgoing Pantos transfers included in a specified
        transaction.

        Parameters
        ----------
        transaction_id : str
            The ID/hash of the transaction.
        hub_address : BlockchainAddress
            The address of the Pantos Hub contract the outgoing
            transfers have been submitted to.

        Returns
        -------
        list of CrossChainTransfer
            The transfer data of the outgoing transfers included in the
            specified transaction.

        Raises
        ------
        BlockchainClientError
            If the outgoing transfers cannot be read.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def read_token_decimals(self, token_address: BlockchainAddress) -> int:
        """Read the decimals of a token.

        Parameters
        ----------
        token_address : BlockchainAddress
            The blockchain address of the token.

        Returns
        -------
        int
            The decimals of the token.

        Raises
        ------
        BlockchainClientError
            If the token decimals cannot be read.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def read_validator_node_addresses(self) -> list[BlockchainAddress]:
        """Read the addresses of all Pantos validator nodes registered
        on the blockchain.

        Returns
        -------
        list of BlockchainAddress
            The validator node addresses.

        Raises
        ------
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainClientError
            If the validator node addresses cannot be read.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class TransferToSignerAddressRecoveryRequest:
        """Request data for recovering the signer's address from a
        Pantos transferTo signature.

        Attributes
        ----------
        source_blockchain : Blockchain
            The source blockchain of the cross-chain token transfer.
        source_transaction_id : str
            The transfer's transaction ID/hash on the source blockchain.
        source_transfer_id : int
            The Pantos transfer ID on the source blockchain.
        sender_address : BlockchainAddress
            The address of the sender on the source blockchain.
        recipient_address : BlockchainAddress
            The address of the recipient on the destination blockchain.
        source_token_address : BlockchainAddress
            The contract address of the transferred PANDAS token on the
            source blockchain.
        destination_token_address : BlockchainAddress
            The contract address of the transferred PANDAS token on the
            destination blockchain.
        amount : int
            The transferred PANDAS token amount.
        validator_nonce : int
            The nonce of the validator nodes at the Pantos Forwarder
            contract of the destination blockchain.
        signature : str
            The signature of a validator node for the cross-chain token
            transfer.

        """
        source_blockchain: Blockchain
        source_transaction_id: str
        source_transfer_id: int
        sender_address: BlockchainAddress
        recipient_address: BlockchainAddress
        source_token_address: BlockchainAddress
        destination_token_address: BlockchainAddress
        amount: int
        validator_nonce: int
        signature: str

    @abc.abstractmethod
    def recover_transfer_to_signer_address(
            self, request: TransferToSignerAddressRecoveryRequest) \
            -> BlockchainAddress:
        """Recover the signer's address from a Pantos transferTo
        signature.

        Parameters
        ----------
        request : TransferToSignerAddressRecoveryRequest
            The request data.

        Returns
        -------
        BlockchainAddress
            The signer's address.

        Raises
        ------
        BlockchainClientError
            If the signer's address cannot be recovered.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class TransferToMessageSignRequest:
        """Request data for signing a Pantos transferTo message.

        Attributes
        ----------
        incoming_transfer : CrossChainTransfer
            The transfer data.
        validator_nonce : int
            The nonce of the validator nodes at the Pantos Forwarder
            contract on the (eventual) destination blockchain.
        destination_hub_address : BlockchainAddress
            The address of the Pantos Hub contract on the (eventual)
            destination blockchain.
        destination_forwarder_address : BlockchainAddress
            The address of the Pantos Forwarder contract on the
            (eventual) destination blockchain.

        """
        incoming_transfer: CrossChainTransfer
        validator_nonce: int
        destination_hub_address: BlockchainAddress
        destination_forwarder_address: BlockchainAddress

    @abc.abstractmethod
    def sign_transfer_to_message(self,
                                 request: TransferToMessageSignRequest) -> str:
        """Sign a Pantos transferTo message.

        Parameters
        ----------
        request : TransferToMessageSignRequest
            The request data.

        Returns
        -------
        str
            The current validator node's signature for the transferTo
            message.

        Raises
        ------
        BlockchainClientError
            If the transferTo message cannot be signed.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class TransferToSubmissionStartRequest:
        """Request data for starting a transferTo submission.

        Attributes
        ----------
        internal_transfer_id : int
            The unique internal ID of the transfer.
        incoming_transfer : CrossChainTransfer
            The transfer data.
        validator_nonce : int
            The nonce of the validator nodes at the Pantos Forwarder
            contract on the (eventual) destination blockchain.
        validator_node_signatures : dict
            The validator node addresses on the (eventual) destination
            blockchain as keys and their corresponding transfer
            signatures as values.

        """
        internal_transfer_id: int
        incoming_transfer: CrossChainTransfer
        validator_nonce: int
        validator_node_signatures: dict[BlockchainAddress, str]

    @abc.abstractmethod
    def start_transfer_to_submission(
            self, request: TransferToSubmissionStartRequest) -> uuid.UUID:
        """Start a transferTo submission. The transaction is
        automatically resubmitted with higher transaction fees until it
        is included in a block.

        Parameters
        ----------
        request : TransferToSubmissionStartRequest
            The request data.

        Returns
        -------
        uuid.UUID
            The unique internal transaction ID.

        Raises
        ------
        NonMatchingForwarderError
            If the Pantos Forwarder of the transferred token does not
            match the Pantos Forwarder of the Pantos Hub on the
            destination blockchain.
        SourceTransferIdAlreadyUsedError
            If the source blockchain's Pantos transfer ID was already
            submitted before for another token transfer.
        BlockchainClientError
            If the transferTo submission cannot be submitted or
            processed for any other reason.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class TransferToSubmissionStatusResponse:
        """Response data from retrieving the status of a transferTo
        submission.

        Attributes
        ----------
        transaction_submission_completed : bool
            True if and only if the transaction submission has been
            completed (i.e. the transaction is either confirmed or
            reverted).
        transaction_status : TransactionStatus or None
            The status of the submitted (and eventually included)
            transaction (available if the transaction submission has
            been completed).
        transaction_id : str or None
            The ID/hash of the submitted (and eventually included)
            transaction (available if the transaction submission has
            been completed).
        block_number : int or None
            The block number of the submitted (and eventually included)
            transaction (available if the transaction submission has
            been completed).
        destination_transfer_id : int or None
            The Pantos transfer ID on the (eventual) destination
            blockchain (available if the transaction has been
            confirmed).

        """
        transaction_submission_completed: bool
        transaction_status: TransactionStatus | None = None
        transaction_id: str | None = None
        block_number: int | None = None
        destination_transfer_id: int | None = None

    def get_transfer_to_submission_status(
            self, internal_transaction_id: uuid.UUID) \
            -> TransferToSubmissionStatusResponse:
        """Retrieve the status of a transferTo submission.

        Parameters
        ----------
        internal_transaction_id : uuid.UUID
            The unique internal transaction ID.

        Returns
        -------
        TransferToSubmissionStatusResponse
            The response data.

        Raises
        ------
        UnresolvableTransferToSubmissionError
            If there has been an unresolvable error during the
            transferTo submission.
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainClientError
            If the tranferTo transaction data cannot be read.

        """
        try:
            status_response = \
                self.get_utilities().get_transaction_submission_status(
                    internal_transaction_id)
        except BlockchainUtilitiesError:
            raise self._create_unresolvable_transfer_to_submission_error(
                internal_transaction_id=internal_transaction_id)
        _logger.info(
            'transferTo transaction submission status',
            extra=vars(status_response)
            | {'internal_transaction_id': internal_transaction_id})
        if not status_response.transaction_submission_completed:
            return BlockchainClient.TransferToSubmissionStatusResponse(False)
        transaction_status = status_response.transaction_status
        assert transaction_status in [
            TransactionStatus.CONFIRMED, TransactionStatus.REVERTED
        ]
        transaction_id = status_response.transaction_id
        assert transaction_id is not None
        data_response = self._read_transfer_to_transaction_data(
            transaction_id, transaction_status is TransactionStatus.CONFIRMED)
        return BlockchainClient.TransferToSubmissionStatusResponse(
            True, transaction_status=transaction_status,
            transaction_id=transaction_id,
            block_number=data_response.block_number,
            destination_transfer_id=data_response.destination_transfer_id)

    @dataclasses.dataclass
    class _TransferToTransactionDataResponse:
        """Response from reading transferTo transaction data.

        Attributes
        ----------
        block_number : int
            The block number of the transaction.
        destination_transfer_id : int or None
            The Pantos transfer ID on the (eventual) destination
            blockchain.

        """
        block_number: int
        destination_transfer_id: int | None = None

    @abc.abstractmethod
    def _read_transfer_to_transaction_data(
            self, transaction_id: str, read_destination_transfer_id: bool) \
            -> _TransferToTransactionDataResponse:
        """Read transferTo transaction data.

        Parameters
        ----------
        transaction_id : str
            The ID/hash of the transaction.
        read_destination_transfer_id : bool
            True if the Pantos transfer ID on the (eventual) destination
            blockchain is to be read and returned.

        Returns
        -------
        _TransferToTransactionDataResponse
            The response data.

        Raises
        ------
        BlockchainClientError
            If the tranferTo transaction data cannot be read.

        """
        pass  # pragma: no cover

    def _get_config(self) -> dict[str, typing.Any]:
        return get_blockchain_config(self.get_blockchain())

    def _create_non_matching_forwarder_error(
            self, **kwargs: typing.Any) -> BlockchainClientError:
        return self._create_error(
            specialized_error_class=NonMatchingForwarderError, **kwargs)

    def _create_source_transfer_id_already_used_error(
            self, **kwargs: typing.Any) -> BlockchainClientError:
        return self._create_error(
            specialized_error_class=SourceTransferIdAlreadyUsedError, **kwargs)

    def _create_unresolvable_transfer_to_submission_error(
            self, **kwargs: typing.Any) -> BlockchainClientError:
        return self._create_error(
            specialized_error_class=UnresolvableTransferToSubmissionError,
            **kwargs)

    @property
    def _versioned_pantos_forwarder_abi(self) -> VersionedContractAbi:
        return VersionedContractAbi(ContractAbi.PANTOS_FORWARDER,
                                    self.protocol_version)

    @property
    def _versioned_pantos_hub_abi(self) -> VersionedContractAbi:
        return VersionedContractAbi(ContractAbi.PANTOS_HUB,
                                    self.protocol_version)

    @property
    def _versioned_pantos_token_abi(self) -> VersionedContractAbi:
        return VersionedContractAbi(ContractAbi.PANTOS_TOKEN,
                                    self.protocol_version)
