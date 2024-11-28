"""Business logic for detecting and validating cross-chain token
transfers.

"""
import abc
import logging
import random
import typing
import uuid

import celery.result  # type: ignore
from pantos.common.blockchains.enums import Blockchain
from pantos.common.entities import TransactionStatus
from pantos.common.types import BlockchainAddress

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.blockchains.base import NonMatchingForwarderError
from pantos.validatornode.blockchains.base import \
    SourceTransferIdAlreadyUsedError
from pantos.validatornode.blockchains.base import \
    UnresolvableTransferToSubmissionError
from pantos.validatornode.blockchains.factory import get_blockchain_client
from pantos.validatornode.business.base import Interactor
from pantos.validatornode.business.base import InteractorError
from pantos.validatornode.celery import celery_app
from pantos.validatornode.configuration import config
from pantos.validatornode.configuration import get_blockchain_config
from pantos.validatornode.database import access as database_access
from pantos.validatornode.database.access import TransferCreationRequest
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.entities import CrossChainTransfer
from pantos.validatornode.entities import CrossChainTransferDict
from pantos.validatornode.restclient import PrimaryNodeClient
from pantos.validatornode.restclient import PrimaryNodeDuplicateSignatureError
from pantos.validatornode.restclient import PrimaryNodeInvalidSignerError

_logger = logging.getLogger(__name__)


class TransferInteractorError(InteractorError):
    """Exception class for all transfer interactor errors.

    """
    pass


class TransferInteractor(Interactor):
    """Interactor for detecting and validating cross-chain token
    transfers.

    """
    @classmethod
    def get_error_class(cls) -> type[InteractorError]:
        # Docstring inherited
        return TransferInteractorError

    def confirm_transfer(self, internal_transfer_id: int,
                         internal_transaction_id: uuid.UUID,
                         transfer: CrossChainTransfer) -> bool:
        """Confirm a cross-chain token transfer on the (eventual)
        destination blockchain.

        Parameters
        ----------
        internal_transfer_id : int
            The unique internal ID of the transfer.
        internal_transaction_id : uuid.UUID
            The unique internal transaction ID.
        transfer : CrossChainTransfer
            The data of the cross-chain token transfer to validate.

        Returns
        -------
        bool
            True if the confirmation is completed for the transfer.

        Raises
        ------
        TransferInteractorError
            If an error occurs during confirming the cross-chain token
            transfer.

        """
        try:
            extra_info = vars(transfer) | {
                'interal_transfer_id': internal_transfer_id,
                'internal_transaction_id': internal_transaction_id
            }
            blockchain_client = get_blockchain_client(
                transfer.eventual_destination_blockchain)
            try:
                status_response = \
                    blockchain_client.get_transfer_to_submission_status(
                        internal_transaction_id)
            except UnresolvableTransferToSubmissionError:
                _logger.error('incoming token transfer failed',
                              extra=extra_info, exc_info=True)
                self.__restart_validation(internal_transfer_id, transfer)
                return True
            if not status_response.transaction_submission_completed:
                _logger.info('incoming token transfer not yet confirmed',
                             extra=extra_info)
                return False
            transaction_status = status_response.transaction_status
            extra_info |= {
                'destination_transaction_id': status_response.transaction_id,
                'destination_block_number': status_response.block_number
            }
            if transaction_status is TransactionStatus.REVERTED:
                _logger.warning('incoming token transfer reverted',
                                extra=extra_info)
                self.__restart_validation(internal_transfer_id, transfer)
                return True
            assert transaction_status is TransactionStatus.CONFIRMED
            extra_info |= {
                'destination_transfer_id': status_response.
                destination_transfer_id
            }
            _logger.info('incoming token transfer confirmed', extra=extra_info)
            assert status_response.transaction_id is not None
            assert status_response.block_number is not None
            assert status_response.destination_transfer_id is not None
            database_access.update_transfer_confirmed_destination_transaction(
                internal_transfer_id, status_response.destination_transfer_id,
                status_response.transaction_id, status_response.block_number)
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_REVERSAL_TRANSACTION_CONFIRMED
                if transfer.is_reversal_transfer else
                TransferStatus.DESTINATION_TRANSACTION_CONFIRMED)
            return True
        except Exception:
            raise self._create_error(
                'unable to determine if a token transfer is confirmed',
                internal_transfer_id=internal_transfer_id,
                internal_transaction_id=internal_transaction_id,
                transfer=transfer)

    def detect_new_transfers(self, source_blockchain: Blockchain) -> None:
        """Detect new cross-chain token transfers on a blockchain.

        Parameters
        ----------
        source_blockchain : Blockchain
            The blockchain to detect new token transfers on.

        Raises
        ------
        TransferInteractorError
            If an error occurs during detecting new cross-chain token
            transfers.

        """
        _logger.info('detecting new outgoing token transfers on '
                     f'{source_blockchain.name}')
        source_blockchain_config = get_blockchain_config(source_blockchain)
        source_blockchain_client = get_blockchain_client(source_blockchain)
        try:
            last_block_number = \
                database_access.read_blockchain_last_block_number(
                    source_blockchain)
            from_block_number = max(
                last_block_number - source_blockchain_config['confirmations'],
                source_blockchain_config['from_block'])
            outgoing_transfers_response = \
                source_blockchain_client.read_outgoing_transfers_from_block(
                    from_block_number)
            found_transfers = outgoing_transfers_response.outgoing_transfers
            to_block_number = outgoing_transfers_response.to_block_number
            if from_block_number > to_block_number:
                assert len(found_transfers) == 0
                if from_block_number - 1 == to_block_number:
                    # The most recent block was already considered in
                    # the last check for outgoing transfers
                    return
                else:
                    raise self._create_error(
                        f'most recent block number "{to_block_number}" is '
                        'smaller than the previously considered block number '
                        f'"{from_block_number - 1}"')
            for found_transfer in found_transfers:
                internal_transfer_id = database_access.read_transfer_id(
                    found_transfer.source_blockchain,
                    found_transfer.source_transaction_id)
                if internal_transfer_id is None:
                    _logger.info('new token transfer',
                                 extra=vars(found_transfer))
                    # Secondary nodes also assign a validator nonce
                    # since they are supposed to be able to assume the
                    # primary role anytime after reconfiguration
                    validator_nonce = self.__find_unused_validator_nonce(
                        found_transfer.destination_blockchain)
                    transfer_creation_request = TransferCreationRequest(
                        found_transfer.source_blockchain,
                        found_transfer.destination_blockchain,
                        found_transfer.sender_address,
                        found_transfer.recipient_address,
                        found_transfer.source_token_address,
                        found_transfer.destination_token_address,
                        found_transfer.amount, validator_nonce,
                        found_transfer.source_hub_address,
                        found_transfer.source_transfer_id,
                        found_transfer.source_transaction_id,
                        found_transfer.source_block_number)
                    internal_transfer_id = database_access.create_transfer(
                        transfer_creation_request)
                    # Schedule the cross-chain transfer to be validated
                    # asynchronously
                    task_result = _schedule_task(validate_transfer_task,
                                                 internal_transfer_id,
                                                 found_transfer)
                    task_id = uuid.UUID(task_result.id)
                    database_access.update_transfer_task_id(
                        internal_transfer_id, task_id)
            # Update the maximum block number that has been considered
            # for detecting new cross-chain transfers
            database_access.update_blockchain_last_block_number(
                source_blockchain, to_block_number)
        except TransferInteractorError:
            raise
        except Exception:
            raise self._create_error(
                'unable to detect new cross-chain token transfers',
                source_blockchain=source_blockchain)

    def get_validator_nonce(self, source_blockchain: Blockchain,
                            source_transaction_id: str) -> int:
        """Get the validator nonce assigned to a cross-chain token
        transfer.

        Parameters
        ----------
        source_blockchain : Blockchain
            The transfer's source blockchain.
        source_transaction_id : str
            The transfer's transaction ID/hash on the source blockchain.

        Returns
        -------
        int
            The transfer's validator nonce.

        Raises
        ------
        UnknownTransferError
            If there is no transfer for the given source blockchain and
            transaction ID/hash.
        TransferInteractorError
            If another error occurs during getting the validator nonce.

        """
        try:
            validator_nonce = \
                database_access.read_validator_nonce_by_source_transaction_id(
                    source_blockchain, source_transaction_id)
            if validator_nonce is None:
                raise self._create_unknown_transfer_error(
                    source_blockchain=source_blockchain,
                    source_transaction_id=source_transaction_id)
            return validator_nonce
        except TransferInteractorError:
            raise
        except Exception:
            raise self._create_error(
                'unable to get a validator nonce',
                source_blockchain=source_blockchain,
                source_transaction_id=source_transaction_id)

    def submit_transfer_to_primary_node(self, internal_transfer_id: int,
                                        transfer: CrossChainTransfer) -> bool:
        """Submit the signature for a cross-chain token transfer after
        its successful validation to the primary validator node.

        Parameters
        ----------
        internal_transfer_id : int
            The unique internal ID of the transfer.
        transfer : CrossChainTransfer
            The data of the cross-chain token transfer to submit.

        Returns
        -------
        bool
            True if the submission is completed for the transfer.

        Raises
        ------
        TransferInteractorError
            If an error occurs during submitting the signature for a
            cross-chain token transfer.

        """
        try:
            extra_info = vars(transfer) | {
                'interal_transfer_id': internal_transfer_id
            }
            if self._is_primary_node():
                _logger.warning(
                    'former secondary node is now the primary node',
                    extra=extra_info)
                _schedule_task(submit_transfer_onchain_task,
                               internal_transfer_id, transfer)
                return True

            primary_node_client = PrimaryNodeClient(
                config['application']['primary_url'])
            # The validator nonce must be queried everytime since the
            # primary node may have changed
            get_request = PrimaryNodeClient.ValidatorNonceGetRequest(
                transfer.source_blockchain, transfer.source_transaction_id)
            validator_nonce = primary_node_client.get_validator_nonce(
                get_request)
            database_access.update_transfer_validator_nonce(
                internal_transfer_id, validator_nonce)

            destination_blockchain_client = get_blockchain_client(
                transfer.eventual_destination_blockchain)
            destination_blockchain_config = get_blockchain_config(
                transfer.eventual_destination_blockchain)
            destination_hub_address = destination_blockchain_config['hub']
            destination_forwarder_address = destination_blockchain_config[
                'forwarder']
            sign_request = BlockchainClient.TransferToMessageSignRequest(
                transfer, validator_nonce, destination_hub_address,
                destination_forwarder_address)
            signature = destination_blockchain_client.\
                sign_transfer_to_message(sign_request)

            extra_info |= {
                'validator_nonce': validator_nonce,
                'destination_hub_address': destination_hub_address,
                'destination_forwarder_address': destination_forwarder_address
            }
            _logger.info(
                'submitting a token transfer signature to the primary node',
                extra=extra_info)
            post_request = PrimaryNodeClient.TransferSignaturePostRequest(
                transfer.source_blockchain, transfer.source_transaction_id,
                signature)
            try:
                primary_node_client.post_transfer_signature(post_request)
            except PrimaryNodeDuplicateSignatureError:
                _logger.warning(
                    'token transfer signature already submitted to the '
                    'primary node', extra=extra_info)
            except PrimaryNodeInvalidSignerError:  # pragma: no cover
                _logger.critical(
                    'secondary node likely not properly registered as '
                    'validator node at Pantos Forwarder', extra=extra_info)
                raise

            own_address = destination_blockchain_client.get_own_address()
            self.__store_validator_node_signature(
                internal_transfer_id, transfer.eventual_destination_blockchain,
                destination_forwarder_address, own_address, signature)
            database_access.update_transfer_submitted_destination_transaction(
                internal_transfer_id, destination_hub_address,
                destination_forwarder_address)
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_REVERSAL_TRANSACTION_SUBMITTED
                if transfer.is_reversal_transfer else
                TransferStatus.DESTINATION_TRANSACTION_SUBMITTED)
            return True
        except Exception:
            raise self._create_error(
                'unable to submit a token transfer signature to the primary '
                'node', internal_transfer_id=internal_transfer_id,
                transfer=transfer)

    def submit_transfer_onchain(self, internal_transfer_id: int,
                                transfer: CrossChainTransfer) -> bool:
        """Submit a cross-chain token transfer after its successful
        validation to the destination blockchain.

        Parameters
        ----------
        internal_transfer_id : int
            The unique internal ID of the transfer.
        transfer : CrossChainTransfer
            The data of the cross-chain token transfer to submit.

        Returns
        -------
        bool
            True if the submission is completed for the transfer.

        Raises
        ------
        TransferInteractorError
            If an error occurs during submitting the cross-chain token
            transfer.

        """
        try:
            extra_info = vars(transfer) | {
                'interal_transfer_id': internal_transfer_id
            }
            if not self._is_primary_node():
                _logger.warning('former primary node is now a secondary node',
                                extra=extra_info)
                _schedule_task(submit_transfer_to_primary_node_task,
                               internal_transfer_id, transfer)
                return True

            destination_blockchain_client = get_blockchain_client(
                transfer.eventual_destination_blockchain)
            destination_blockchain_config = get_blockchain_config(
                transfer.eventual_destination_blockchain)
            destination_hub_address = destination_blockchain_config['hub']
            destination_forwarder_address = destination_blockchain_config[
                'forwarder']
            validator_nonce = database_access.\
                read_validator_nonce_by_internal_transfer_id(
                    internal_transfer_id)
            assert validator_nonce is not None
            available_signatures = database_access.\
                read_validator_node_signatures(internal_transfer_id)
            extra_info |= {
                'validator_nonce': validator_nonce,
                'destination_hub_address': destination_hub_address,
                'destination_forwarder_address': destination_forwarder_address
            }

            if not self.__sufficient_secondary_node_signatures(
                    transfer, validator_nonce, available_signatures,
                    destination_blockchain_client, extra_info):
                _logger.info(
                    'insufficient signatures for submitting a token transfer '
                    'to the destination blockchain', extra=extra_info)
                return False
            self.__add_primary_node_signature(available_signatures, transfer,
                                              validator_nonce,
                                              destination_hub_address,
                                              destination_forwarder_address,
                                              destination_blockchain_client)

            _logger.info(
                'submitting a token transfer to the destination blockchain',
                extra=extra_info)
            internal_transaction_id = self.__submit_transaction(
                internal_transfer_id, transfer, validator_nonce,
                available_signatures, destination_blockchain_client)

            primary_node_address = \
                destination_blockchain_client.get_own_address()
            self.__store_validator_node_signature(
                internal_transfer_id, transfer.eventual_destination_blockchain,
                destination_forwarder_address, primary_node_address,
                available_signatures[primary_node_address])
            database_access.update_transfer_submitted_destination_transaction(
                internal_transfer_id, destination_hub_address,
                destination_forwarder_address)
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_REVERSAL_TRANSACTION_SUBMITTED
                if transfer.is_reversal_transfer else
                TransferStatus.DESTINATION_TRANSACTION_SUBMITTED)
            _schedule_task(confirm_transfer_task, internal_transfer_id,
                           transfer, internal_transaction_id)
            return True
        except TransferInteractor.__PermanentTransferSubmissionError:
            return True
        except Exception:
            raise self._create_error(
                'unable to submit a token transfer to the destination '
                'blockchain', internal_transfer_id=internal_transfer_id,
                transfer=transfer)

    def validate_transfer(self, internal_transfer_id: int,
                          transfer: CrossChainTransfer) -> bool:
        """Validate a cross-chain token transfer.

        Parameters
        ----------
        internal_transfer_id : int
            The unique internal ID of the transfer.
        transfer : CrossChainTransfer
            The data of the cross-chain token transfer to validate.

        Returns
        -------
        bool
            True if the validation is completed for the transfer.

        Raises
        ------
        TransferInteractorError
            If an error occurs during validating the cross-chain token
            transfer.

        """
        extra_info = vars(transfer) | {
            'interal_transfer_id': internal_transfer_id
        }
        _logger.info('validating a token transfer', extra=extra_info)
        try:
            source_blockchain_client = get_blockchain_client(
                transfer.source_blockchain)
            destination_blockchain_client = get_blockchain_client(
                transfer.destination_blockchain)
            self.__validate_source_transaction_status(
                internal_transfer_id, transfer, source_blockchain_client)
            self.__validate_transfer_in_source_transaction(
                internal_transfer_id, transfer, source_blockchain_client)
            self.__validate_source_token_registration(
                internal_transfer_id, transfer, source_blockchain_client)
            self.__validate_destination_blockchain_feasibility(
                internal_transfer_id, transfer, source_blockchain_client,
                destination_blockchain_client)
            _logger.info(
                'incoming token transfer not feasible'
                if transfer.is_reversal_transfer else
                'outgoing token transfer confirmed', extra=extra_info)
            if transfer.is_reversal_transfer:
                database_access.update_reversal_transfer(
                    internal_transfer_id,
                    transfer.eventual_destination_blockchain,
                    transfer.eventual_recipient_address,
                    transfer.eventual_destination_token_address)
            if self._is_primary_node():
                _schedule_task(submit_transfer_onchain_task,
                               internal_transfer_id, transfer)
            else:
                _schedule_task(submit_transfer_to_primary_node_task,
                               internal_transfer_id, transfer)
            return True
        except TransferInteractor.__TransferValidationError as error:
            return error.is_permanent()
        except TransferInteractorError:
            raise
        except Exception:
            raise self._create_error('unable to validate a token transfer',
                                     internal_transfer_id=internal_transfer_id,
                                     transfer=transfer)

    class __PermanentTransferSubmissionError(Exception):
        pass

    class __TransferValidationError(Exception, abc.ABC):
        @abc.abstractmethod
        def is_permanent(self) -> bool:
            pass  # pragma: no cover

    class __PermanentTransferValidationError(__TransferValidationError):
        def is_permanent(self) -> bool:
            return True

    class __TransitoryTransferValidationError(__TransferValidationError):
        def is_permanent(self) -> bool:
            return False

    def __add_primary_node_signature(
            self, signatures: dict[BlockchainAddress,
                                   str], transfer: CrossChainTransfer,
            validator_nonce: int, destination_hub_address: BlockchainAddress,
            destination_forwarder_address: BlockchainAddress,
            destination_blockchain_client: BlockchainClient) -> None:
        assert self._is_primary_node()
        primary_node_address = destination_blockchain_client.get_own_address()
        sign_request = BlockchainClient.TransferToMessageSignRequest(
            transfer, validator_nonce, destination_hub_address,
            destination_forwarder_address)
        primary_node_signature = destination_blockchain_client.\
            sign_transfer_to_message(sign_request)
        signatures[primary_node_address] = primary_node_signature

    def __store_validator_node_signature(
            self, internal_transfer_id: int,
            destination_blockchain: Blockchain,
            destination_forwarder_address: BlockchainAddress,
            validator_node_address: BlockchainAddress, signature: str) -> None:
        # Read the signature first for improved error resilience during
        # retries
        stored_signature = database_access.read_validator_node_signature(
            internal_transfer_id, destination_blockchain,
            destination_forwarder_address, validator_node_address)
        if stored_signature is None:
            database_access.create_validator_node_signature(
                internal_transfer_id, destination_blockchain,
                destination_forwarder_address, validator_node_address,
                signature)

    def __find_unused_validator_nonce(
            self, destination_blockchain: Blockchain) -> int:
        destination_blockchain_client = get_blockchain_client(
            destination_blockchain)
        while True:
            validator_nonce = random.getrandbits(256)
            if destination_blockchain_client.is_valid_validator_nonce(
                    validator_nonce):
                return validator_nonce

    def __restart_validation(self, internal_transfer_id: int,
                             transfer: CrossChainTransfer) -> None:
        database_access.reset_transfer_nonce(internal_transfer_id)
        database_access.update_transfer_status(
            internal_transfer_id, TransferStatus.SOURCE_TRANSACTION_DETECTED)
        task_result = _schedule_task(validate_transfer_task,
                                     internal_transfer_id, transfer)
        task_id = uuid.UUID(task_result.id)
        database_access.update_transfer_task_id(internal_transfer_id, task_id)

    def __submit_transaction(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            validator_nonce: int, signatures: dict[BlockchainAddress, str],
            destination_blockchain_client: BlockchainClient) -> uuid.UUID:
        request = BlockchainClient.TransferToSubmissionStartRequest(
            internal_transfer_id, transfer, validator_nonce, signatures)
        try:
            return destination_blockchain_client.start_transfer_to_submission(
                request)
        except (NonMatchingForwarderError,
                SourceTransferIdAlreadyUsedError) as error:
            _logger.error(
                'non-matching Forwarder' if isinstance(
                    error, NonMatchingForwarderError) else
                'source transfer ID already used', exc_info=True,
                extra=error.details)
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED
                if transfer.is_reversal_transfer else
                TransferStatus.DESTINATION_TRANSACTION_FAILED)
            raise TransferInteractor.__PermanentTransferSubmissionError
        except Exception:
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED
                if transfer.is_reversal_transfer else
                TransferStatus.DESTINATION_TRANSACTION_FAILED)
            raise

    def __sufficient_secondary_node_signatures(
            self, transfer: CrossChainTransfer, validator_nonce: int,
            signatures: dict[BlockchainAddress, str],
            destination_blockchain_client: BlockchainClient,
            extra_info: dict[str, typing.Any]) -> bool:
        assert self._is_primary_node()
        valid_signatures = 1  # Primary node signature
        primary_node_address = destination_blockchain_client.get_own_address()
        for signer_address, signature in signatures.items():
            if signer_address == primary_node_address:
                continue
            signer_recovery_request = \
                BlockchainClient.TransferToSignerAddressRecoveryRequest(
                    transfer.source_blockchain, transfer.source_transaction_id,
                    transfer.source_transfer_id, transfer.sender_address,
                    transfer.recipient_address, transfer.source_token_address,
                    transfer.eventual_destination_token_address,
                    transfer.amount, validator_nonce, signature)
            try:
                recovered_signer_address = destination_blockchain_client.\
                    recover_transfer_to_signer_address(signer_recovery_request)
            except BlockchainClientError:
                _logger.critical(
                    'invalid secondary node signature for submitting a token '
                    'transfer to the destination blockchain',
                    extra=extra_info | {
                        'signer_address': signer_address,
                        'signature': signature
                    }, exc_info=True)
                continue
            assert destination_blockchain_client.is_equal_address(
                signer_address, recovered_signer_address)
            valid_signatures += 1
        minimum_signatures = destination_blockchain_client.\
            read_minimum_validator_node_signatures()
        return valid_signatures >= minimum_signatures

    def __validate_destination_blockchain_feasibility(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            source_blockchain_client: BlockchainClient,
            destination_blockchain_client: BlockchainClient) -> None:
        try:
            self.__validate_transfer_recipient_address(
                internal_transfer_id, transfer, destination_blockchain_client)
            self.__validate_destination_token_registration(
                internal_transfer_id, transfer, destination_blockchain_client)
            self.__validate_token_addresses(internal_transfer_id, transfer,
                                            source_blockchain_client,
                                            destination_blockchain_client)
            self.__validate_token_decimals(internal_transfer_id, transfer,
                                           source_blockchain_client,
                                           destination_blockchain_client)
        except TransferInteractor.__TransferValidationError as error:
            if not error.is_permanent():
                raise
            # The transfer is permanently not feasible to be submitted
            # to the destination blockchain and can only be reversed
            # (i.e. the tokens have to be sent back to the sender on the
            # source blockchain)
            transfer.is_reversal_transfer = True

    def __validate_destination_token_registration(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            destination_blockchain_client: BlockchainClient) -> None:
        destination_token_active = \
            destination_blockchain_client.is_token_active(
                transfer.destination_token_address)
        if not destination_token_active:
            _logger.info(
                'outgoing token transfer invalid '
                '(destination token not registered)', extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_transfer_id': transfer.source_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name
                })
            raise TransferInteractor.__PermanentTransferValidationError

    def __validate_source_token_registration(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            source_blockchain_client: BlockchainClient) -> None:
        source_token_active = source_blockchain_client.is_token_active(
            transfer.source_token_address)
        if not source_token_active:
            _logger.info(
                'outgoing token transfer invalid '
                '(source token not registered)', extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_transfer_id': transfer.source_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name
                })
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_TRANSACTION_INVALID)
            raise TransferInteractor.__PermanentTransferValidationError

    def __validate_token_addresses(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            source_blockchain_client: BlockchainClient,
            destination_blockchain_client: BlockchainClient) -> None:
        source_token_address = typing.cast(
            BlockchainAddress,
            destination_blockchain_client.read_external_token_address(
                transfer.destination_token_address,
                transfer.source_blockchain))
        destination_token_address = typing.cast(
            BlockchainAddress,
            source_blockchain_client.read_external_token_address(
                transfer.source_token_address,
                transfer.destination_blockchain))
        if (not source_blockchain_client.is_equal_address(
                source_token_address, transfer.source_token_address)
                or not destination_blockchain_client.is_equal_address(
                    destination_token_address,
                    transfer.destination_token_address)):
            _logger.info(
                'outgoing token transfer invalid '
                '(non-matching source and destination token addresses)',
                extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_transfer_id': transfer.source_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name
                })
            raise TransferInteractor.__PermanentTransferValidationError

    def __validate_token_decimals(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            source_blockchain_client: BlockchainClient,
            destination_blockchain_client: BlockchainClient) -> None:
        source_token_decimals = source_blockchain_client.read_token_decimals(
            transfer.source_token_address)
        destination_token_decimals = \
            destination_blockchain_client.read_token_decimals(
                transfer.destination_token_address)
        if source_token_decimals != destination_token_decimals:
            _logger.info(
                'outgoing token transfer invalid '
                '(non-matching source and destination token decimals)', extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_transfer_id': transfer.source_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name
                })
            raise TransferInteractor.__PermanentTransferValidationError

    def __validate_transfer_in_source_transaction(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            source_blockchain_client: BlockchainClient) -> None:
        transfers_in_transaction = source_blockchain_client.\
            read_outgoing_transfers_in_transaction(
                transfer.source_transaction_id, transfer.source_hub_address)
        if transfer not in transfers_in_transaction:
            transfer_found = False
            for transfer_in_transaction in transfers_in_transaction:
                # The transfer ID assigned automatically by the Pantos
                # Hub can change if the transaction is actually included
                # in another block than initially assumed by our
                # blockchain node
                transfer.source_transfer_id = \
                    transfer_in_transaction.source_transfer_id
                transfer.source_block_number = \
                    transfer_in_transaction.source_block_number
                transfer.source_block_hash = \
                    transfer_in_transaction.source_block_hash
                if transfer == transfer_in_transaction:
                    transfer_found = True
                    database_access.update_transfer_source_transaction(
                        internal_transfer_id, transfer.source_transfer_id,
                        transfer.source_block_number)
                    break
            if not transfer_found:
                raise self._create_error(
                    'transfer not found in source transaction',
                    internal_transfer_id=internal_transfer_id,
                    transfer=transfer)

    def __validate_transfer_recipient_address(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            destination_blockchain_client: BlockchainClient) -> None:
        if not destination_blockchain_client.is_valid_recipient_address(
                transfer.recipient_address):
            _logger.info(
                'outgoing token transfer invalid (recipient address invalid)',
                extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name,
                    'source_transaction_id': transfer.source_transaction_id,
                    'source_transfer_id': transfer.source_transfer_id
                })
            raise TransferInteractor.__PermanentTransferValidationError

    def __validate_source_transaction_status(
            self, internal_transfer_id: int, transfer: CrossChainTransfer,
            source_blockchain_client: BlockchainClient) -> None:
        transaction_status = \
            source_blockchain_client.get_utilities().read_transaction_status(
                transfer.source_transaction_id)
        if transaction_status in [
                TransactionStatus.UNINCLUDED, TransactionStatus.UNCONFIRMED
        ]:
            _logger.info(
                'outgoing token transfer not yet '
                f'{transaction_status.name.lower()[2:]}', extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_transfer_id': transfer.source_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name
                })
            raise TransferInteractor.__TransitoryTransferValidationError
        if transaction_status is TransactionStatus.REVERTED:
            _logger.info(
                'outgoing token transfer reverted', extra={
                    'internal_transfer_id': internal_transfer_id,
                    'source_transfer_id': transfer.source_transfer_id,
                    'source_blockchain': transfer.source_blockchain.name
                })
            database_access.update_transfer_status(
                internal_transfer_id,
                TransferStatus.SOURCE_TRANSACTION_REVERTED)
            raise TransferInteractor.__PermanentTransferValidationError
        assert transaction_status is TransactionStatus.CONFIRMED


@celery_app.task(bind=True, max_retries=None)
def confirm_transfer_task(self, internal_transfer_id: int,
                          internal_transaction_id: str,
                          transfer_dict: CrossChainTransferDict) -> bool:
    """Celery task for confirming a cross-chain token transfer on the
    (eventual) destination blockchain.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    internal_transaction_id : str
        The unique internal transaction ID.
    transfer_dict : CrossChainTransferDict
        The data of the cross-chain token transfer to confirm.

    Returns
    -------
    bool
        True if the task is executed without error.

    """
    transfer = CrossChainTransfer.from_dict(transfer_dict)
    try:
        confirmation_completed = TransferInteractor().confirm_transfer(
            internal_transfer_id, uuid.UUID(internal_transaction_id), transfer)
    except Exception as error:
        _logger.error(
            'unable to confirm a token transfer on the destination blockchain',
            extra=vars(transfer)
            | {
                'internal_transfer_id': internal_transfer_id,
                'internal_transaction_id': internal_transaction_id,
                'task_id': self.request.id
            }, exc_info=True)
        retry_interval = _get_task_interval(self, after_error=True)
        raise self.retry(countdown=retry_interval, exc=error)
    if not confirmation_completed:
        retry_interval = _get_task_interval(self)
        raise self.retry(countdown=retry_interval)
    return True


@celery_app.task(bind=True, max_retries=None)
def submit_transfer_to_primary_node_task(
        self, internal_transfer_id: int,
        transfer_dict: CrossChainTransferDict) -> bool:
    """Celery task for submitting the signature for a cross-chain token
    transfer after its successful validation to the primary validator
    node.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    transfer_dict : CrossChainTransferDict
        The data of the cross-chain token transfer to submit.

    Returns
    -------
    bool
        True if the task is executed without error.

    """
    transfer = CrossChainTransfer.from_dict(transfer_dict)
    try:
        submission_completed = \
            TransferInteractor().submit_transfer_to_primary_node(
                internal_transfer_id, transfer)
    except Exception as error:
        _logger.error(
            'unable to submit the signature for a token transfer to the '
            'primary validator node', extra=vars(transfer) | {
                'internal_transfer_id': internal_transfer_id,
                'task_id': self.request.id
            }, exc_info=True)
        retry_interval = _get_task_interval(self, after_error=True)
        raise self.retry(countdown=retry_interval, exc=error)
    if not submission_completed:
        retry_interval = _get_task_interval(self)
        raise self.retry(countdown=retry_interval)
    return True


@celery_app.task(bind=True, max_retries=None)
def submit_transfer_onchain_task(
        self, internal_transfer_id: int,
        transfer_dict: CrossChainTransferDict) -> bool:
    """Celery task for submitting a cross-chain token transfer after its
    successful validation to the destination blockchain.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    transfer_dict : CrossChainTransferDict
        The data of the cross-chain token transfer to submit.

    Returns
    -------
    bool
        True if the task is executed without error.

    """
    transfer = CrossChainTransfer.from_dict(transfer_dict)
    try:
        submission_completed = TransferInteractor().submit_transfer_onchain(
            internal_transfer_id, transfer)
    except Exception as error:
        _logger.error(
            'unable to submit a token transfer to the destination blockchain',
            extra=vars(transfer)
            | {
                'internal_transfer_id': internal_transfer_id,
                'task_id': self.request.id
            }, exc_info=True)
        retry_interval = _get_task_interval(self, after_error=True)
        raise self.retry(countdown=retry_interval, exc=error)
    if not submission_completed:
        retry_interval = _get_task_interval(self)
        raise self.retry(countdown=retry_interval)
    return True


@celery_app.task(bind=True, max_retries=None)
def validate_transfer_task(self, internal_transfer_id: int,
                           transfer_dict: CrossChainTransferDict) -> bool:
    """Celery task for validating a cross-chain token transfer.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    transfer_dict : CrossChainTransferDict
        The data of the cross-chain token transfer to validate.

    Returns
    -------
    bool
        True if the task is executed without error.

    """
    transfer = CrossChainTransfer.from_dict(transfer_dict)
    try:
        validation_completed = TransferInteractor().validate_transfer(
            internal_transfer_id, transfer)
    except Exception as error:
        _logger.error(
            'unable to validate a token transfer', extra=vars(transfer)
            | {
                'internal_transfer_id': internal_transfer_id,
                'task_id': self.request.id
            }, exc_info=True)
        retry_interval = _get_task_interval(self, after_error=True)
        raise self.retry(countdown=retry_interval, exc=error)
    if not validation_completed:
        retry_interval = _get_task_interval(self)
        raise self.retry(countdown=retry_interval)
    return True


def _get_task_interval(task, after_error: bool = False) -> int:
    task_name = _get_task_name(task)
    interval_name = ('retry_interval_after_error_in_seconds'
                     if after_error else 'retry_interval_in_seconds')
    return config['tasks'][task_name][interval_name]


def _get_task_name(task) -> str:
    assert task.__name__.endswith('_task')
    return task.__name__[:-5]


def _schedule_task(
        task, internal_transfer_id: int, transfer: CrossChainTransfer,
        internal_transaction_id: uuid.UUID | None = None) \
        -> celery.result.AsyncResult:
    transfer_dict = transfer.to_dict()
    args = ((internal_transfer_id,
             transfer_dict) if internal_transaction_id is None else
            (internal_transfer_id, str(internal_transaction_id),
             transfer_dict))
    countdown = _get_task_interval(task)
    return task.apply_async(args=args, countdown=countdown)
