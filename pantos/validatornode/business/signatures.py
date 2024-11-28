"""Business logic for managing validator node signatures.

"""
import dataclasses
import logging
import typing

from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.blockchains.factory import get_blockchain_client
from pantos.validatornode.business.base import Interactor
from pantos.validatornode.business.base import InteractorError
from pantos.validatornode.configuration import get_blockchain_config
from pantos.validatornode.database import access as database_access
from pantos.validatornode.database.access import TransferToDataResponse

_logger = logging.getLogger(__name__)


class SignatureInteractorError(InteractorError):
    """Exception class for all signature interactor errors.

    """
    pass


class SignatureInteractor(Interactor):
    """Interactor for managing validator node signatures.

    """
    @classmethod
    def get_error_class(cls) -> type[InteractorError]:
        # Docstring inherited
        return SignatureInteractorError

    @dataclasses.dataclass
    class SecondaryNodeSignatureAddRequest:
        """Request data for adding a secondary node signature for a
        cross-chain transfer.

        Attributes
        ----------
        source_blockchain : Blockchain
            The transfer's source blockchain.
        source_transaction_id : str
            The transfer's transaction ID/hash on the source blockchain.
        signature : str
            The transfer signature of the secondary node.

        """
        source_blockchain: Blockchain
        source_transaction_id: str
        signature: str

    def add_secondary_node_signature(
            self, request: SecondaryNodeSignatureAddRequest) -> None:
        """Add a secondary node signature for a cross-chain transfer.

        Parameters
        ----------
        request : SecondaryNodeSignatureAddRequest
            The request data.

        Raises
        ------
        DuplicateSignatureError
            If the secondary node's transfer signature is already
            existing.
        InvalidSignatureError
            If the secondary node's transfer signature is invalid (i.e.
            the signer is not recoverable).
        InvalidSignerError
            If the signer of the transfer signature is not a validator
            node on the transfer's destination blockchain.
        UnknownTransferError
            If no transfer is known for the given source blockchain and
            transaction ID/hash.
        SignatureInteractorError
            If another error occurs during adding the secondary node
            signature.

        """
        try:
            extra_info = vars(request)
            transfer_to_data = self.__read_transfer_to_data(
                request, extra_info)
            extra_info |= vars(transfer_to_data)
            destination_blockchain_client = get_blockchain_client(
                transfer_to_data.destination_blockchain)
            destination_forwarder_address = get_blockchain_config(
                transfer_to_data.destination_blockchain)['forwarder']
            signer_address = self.__recover_transfer_to_signer_address(
                request, transfer_to_data, destination_blockchain_client,
                extra_info)
            extra_info |= {'signer_address': signer_address}
            self.__verify_signature_not_existing(
                request, transfer_to_data, destination_forwarder_address,
                signer_address, extra_info)
            self.__verify_signer_is_validator_node(
                request, signer_address, destination_blockchain_client,
                extra_info)
            database_access.create_validator_node_signature(
                transfer_to_data.internal_transfer_id,
                transfer_to_data.destination_blockchain,
                destination_forwarder_address, signer_address,
                request.signature)
            _logger.info('secondary node signature added', extra=extra_info)
        except SignatureInteractorError:
            raise
        except Exception:
            raise self._create_error(
                'unable to add a secondary node signature', request=request)

    def __read_transfer_to_data(
            self, request: SecondaryNodeSignatureAddRequest,
            extra_info: dict[str, typing.Any]) -> TransferToDataResponse:
        transfer_to_data = database_access.read_transfer_to_data(
            request.source_blockchain, request.source_transaction_id)
        if transfer_to_data is None:
            _logger.warning('unknown transfer for secondary node signature',
                            extra=extra_info)
            raise self._create_unknown_transfer_error(request=request)
        return transfer_to_data

    def __recover_transfer_to_signer_address(
            self, request: SecondaryNodeSignatureAddRequest,
            transfer_to_data: TransferToDataResponse,
            destination_blockchain_client: BlockchainClient,
            extra_info: dict[str, typing.Any]) -> BlockchainAddress:
        signer_recovery_request = \
            BlockchainClient.TransferToSignerAddressRecoveryRequest(
                request.source_blockchain, request.source_transaction_id,
                transfer_to_data.source_transfer_id,
                transfer_to_data.sender_address,
                transfer_to_data.recipient_address,
                transfer_to_data.source_token_address,
                transfer_to_data.destination_token_address,
                transfer_to_data.amount, transfer_to_data.validator_nonce,
                request.signature)
        try:
            return destination_blockchain_client.\
                recover_transfer_to_signer_address(signer_recovery_request)
        except BlockchainClientError:
            _logger.warning('unrecoverable secondary node signer',
                            extra=extra_info, exc_info=True)
            raise self._create_invalid_signature_error(request=request)

    def __verify_signature_not_existing(
            self, request: SecondaryNodeSignatureAddRequest,
            transfer_to_data: TransferToDataResponse,
            destination_forwarder_address: BlockchainAddress,
            signer_address: BlockchainAddress,
            extra_info: dict[str, typing.Any]) -> None:
        existing_signature = database_access.read_validator_node_signature(
            transfer_to_data.internal_transfer_id,
            transfer_to_data.destination_blockchain,
            destination_forwarder_address, signer_address)
        if existing_signature is not None:
            extra_info |= {'existing_signature': existing_signature}
            _logger.warning('secondary node signature already existing',
                            extra=extra_info)
            raise self._create_duplicate_signature_error(request=request)

    def __verify_signer_is_validator_node(
            self, request: SecondaryNodeSignatureAddRequest,
            signer_address: BlockchainAddress,
            destination_blockchain_client: BlockchainClient,
            extra_info: dict[str, typing.Any]) -> None:
        validator_node_addresses = \
            destination_blockchain_client.read_validator_node_addresses()
        if signer_address not in validator_node_addresses:
            _logger.critical('signer is not a validator node',
                             extra=extra_info)
            raise self._create_invalid_signer_error(request=request)
