"""Module for Ethereum-specific clients and errors.

"""
import json
import logging
import re
import typing
import urllib.parse
import uuid

import eth_account.messages
import web3
import web3.contract
import web3.exceptions
import web3.providers.rpc
import web3.types
from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import NodeConnections
from pantos.common.blockchains.base import ResultsNotMatchingError
from pantos.common.blockchains.base import TransactionNonceTooLowError
from pantos.common.blockchains.base import TransactionUnderpricedError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.types import BlockchainAddress

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import BlockchainClientError
from pantos.validatornode.database import access as database_access
from pantos.validatornode.entities import CrossChainTransfer

_HUB_TRANSFER_TO_FUNCTION_SELECTOR = '0x92557c8a'
_HUB_TRANSFER_TO_BASE_GAS = 150000
_HUB_TRANSFER_TO_GAS_PER_SIGNER = 100000

_NON_MATCHING_FORWARDER_ERROR = \
    'PantosHub: Forwarder of Hub and transferred token must match'
_SOURCE_TRANSFER_ID_ALREADY_USED_ERROR = \
    'PantosHub: source transfer ID already used'

_TRANSACTION_ID_PATTERN = re.compile(r'^0x[a-fA-F0-9]{64}')

_EIP712_DOMAIN_NAME = 'Pantos'

_TRANSFER_TO_MESSAGE_TYPES = {
    'TransferToRequest': [{
        'name': 'sourceBlockchainId',
        'type': 'uint256'
    }, {
        'name': 'sourceTransferId',
        'type': 'uint256'
    }, {
        'name': 'sourceTransactionId',
        'type': 'string'
    }, {
        'name': 'sender',
        'type': 'string'
    }, {
        'name': 'recipient',
        'type': 'address'
    }, {
        'name': 'sourceToken',
        'type': 'string'
    }, {
        'name': 'destinationToken',
        'type': 'address'
    }, {
        'name': 'amount',
        'type': 'uint256'
    }, {
        'name': 'nonce',
        'type': 'uint256'
    }],
    'TransferTo': [{
        'name': 'request',
        'type': 'TransferToRequest'
    }, {
        'name': 'destinationBlockchainId',
        'type': 'uint256'
    }, {
        'name': 'pantosHub',
        'type': 'address'
    }, {
        'name': 'pantosForwarder',
        'type': 'address'
    }, {
        'name': 'pantosToken',
        'type': 'address'
    }]
}

_logger = logging.getLogger(__name__)

_Contract: typing.TypeAlias = NodeConnections.Wrapper[web3.contract.Contract]
_OnChainTransferToRequest = tuple[int, int, str, str, str, str, str, int, int]


class EthereumClientError(BlockchainClientError):
    """Exception class for all Ethereum client errors.

    """
    pass


class EthereumClient(BlockchainClient):
    """Ethereum-specific blockchain client.

    """
    def __init__(self):
        """Construct an Ethereum client instance.

        """
        super().__init__()
        private_key = self._get_config()['private_key']
        private_key_password = self._get_config()['private_key_password']
        self.__private_key = self.get_utilities().decrypt_private_key(
            private_key, private_key_password)
        self.__address = self.get_utilities().get_address(self.__private_key)

    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.ETHEREUM

    @classmethod
    def get_error_class(cls) -> type[BlockchainClientError]:
        # Docstring inherited
        return EthereumClientError

    def get_own_address(self) -> BlockchainAddress:
        # Docstring inherited
        return self.__address

    def get_utilities(self) -> EthereumUtilities:
        # Docstring inherited
        return typing.cast(EthereumUtilities, super().get_utilities())

    def is_token_active(self, token_address: BlockchainAddress) -> bool:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            hub_contract = self._create_hub_contract(node_connections)
            token_record = hub_contract.functions.getTokenRecord(
                token_address).call().get()
            assert len(token_record) == 1
            assert isinstance(token_record[0], bool)
            token_active = token_record[0]
            return token_active
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to determine if a token is active',
                token_address=token_address)

    def is_valid_recipient_address(self, recipient_address: str) -> bool:
        # Docstring inherited
        try:
            checksum_address = web3.Web3.to_checksum_address(recipient_address)
        except ValueError:
            # No valid address
            return False
        is_zero_address = int(checksum_address, 0) == 0
        return not is_zero_address

    def is_valid_transaction_id(self, transaction_id: str) -> bool:
        # Docstring inherited
        return (re.fullmatch(_TRANSACTION_ID_PATTERN, transaction_id)
                is not None)

    def is_valid_validator_nonce(self, nonce: int) -> bool:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            hub_contract = self._create_hub_contract(node_connections)
            return hub_contract.caller().isValidValidatorNodeNonce(nonce).get()
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to determine if a validator node nonce is valid',
                nonce=nonce)

    def is_equal_address(self, address_one: BlockchainAddress,
                         address_two: BlockchainAddress) -> bool:
        # Docstring inherited
        return self.get_utilities().is_equal_address(address_one, address_two)

    def read_external_token_address(
            self, token_address: BlockchainAddress,
            external_blockchain: Blockchain) -> BlockchainAddress | None:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            hub_contract = self._create_hub_contract(node_connections)
            external_token_record = \
                hub_contract.functions.getExternalTokenRecord(
                    token_address, external_blockchain.value).call().get()
            assert len(external_token_record) == 2
            assert isinstance(external_token_record[0], bool)
            assert isinstance(external_token_record[1], str)
            active = external_token_record[0]
            if not active:
                return None
            external_token_address = BlockchainAddress(
                external_token_record[1])
            return external_token_address
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read an external token address',
                token_address=token_address,
                external_blockchain=external_blockchain)

    def read_minimum_validator_node_signatures(self) -> int:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            forwarder_contract = self._create_forwarder_contract(
                node_connections)
            minimum_signatures = forwarder_contract.caller().\
                getMinimumValidatorNodeSignatures().get()
            assert minimum_signatures > 0
            return minimum_signatures
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read the minimum validator node signatures')

    def read_outgoing_transfers_from_block(self, from_block_number: int) -> \
            BlockchainClient.ReadOutgoingTransfersFromBlockResponse:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            latest_block_number = \
                node_connections.eth.get_block_number().get_minimum_result()
            if from_block_number > latest_block_number:
                return BlockchainClient.ReadOutgoingTransfersFromBlockResponse(
                    [], latest_block_number)
            _logger.info(
                f'reading outgoing transfers on {self.get_blockchain_name()} '
                f'from block {from_block_number} to block '
                f'{latest_block_number} using node '
                f'{self.__get_blockchain_nodes_domains(node_connections)}')
            hub_contract = self._create_hub_contract(node_connections)
            event = hub_contract.events.TransferFromSucceeded()
            number_blocks = \
                self._get_config()['outgoing_transfers_number_blocks']
            to_block_numbers = list(
                range(from_block_number + number_blocks, latest_block_number,
                      number_blocks)) + [latest_block_number]
            # All TransferFromSucceeded events included in blocks
            # between the specified block numbers
            event_logs: list[web3.types.EventData] = []
            for to_block_number in to_block_numbers:
                assert to_block_number >= from_block_number
                event_logs += self.get_utilities().get_logs(
                    event, from_block_number, to_block_number)
                from_block_number = to_block_number + 1
            outgoing_transfers = self.__create_outgoing_transfers(
                event_logs, hub_contract.address.get())
            return BlockchainClient.ReadOutgoingTransfersFromBlockResponse(
                outgoing_transfers, latest_block_number)
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read outgoing transfers from a starting block',
                from_block_number=from_block_number)

    def read_outgoing_transfers_in_transaction(
            self, transaction_id: str,
            hub_address: BlockchainAddress) -> list[CrossChainTransfer]:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            transaction_receipt = node_connections.eth.get_transaction_receipt(
                typing.cast(web3.types.HexStr, transaction_id)).get()
            assert (transaction_receipt['transactionHash'].to_0x_hex() ==
                    transaction_id)
            hub_contract = self._create_hub_contract(node_connections,
                                                     hub_address)
            event = hub_contract.events.TransferFromSucceeded()
            event_logs = event.process_receipt(transaction_receipt,
                                               errors=web3.logs.DISCARD).get()
            return self.__create_outgoing_transfers(event_logs, hub_address)
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read outgoing transfers in a transaction',
                transaction_id=transaction_id, hub_address=hub_address)

    def read_token_decimals(self, token_address: BlockchainAddress) -> int:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            token_contract = self._create_token_contract(
                node_connections, token_address)
            decimals = token_contract.functions.decimals().call().get()
            assert isinstance(decimals, int)
            return decimals
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error('unable to read the decimals of a token',
                                     token_address=token_address)

    def read_validator_node_addresses(self) -> list[BlockchainAddress]:
        # Docstring inherited
        try:
            node_connections = self.__create_node_connections()
            forwarder_contract = self._create_forwarder_contract(
                node_connections)
            validator_node_addresses = \
                forwarder_contract.caller().getValidatorNodes().get()
            return [
                BlockchainAddress(validator_node_address)
                for validator_node_address in validator_node_addresses
            ]
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read the validator node addresses')

    def recover_transfer_to_signer_address(
            self,
            request: BlockchainClient.TransferToSignerAddressRecoveryRequest) \
            -> BlockchainAddress:
        # Docstring inherited
        destination_blockchain = self.get_blockchain()
        hub_address = self._get_config()['hub']
        forwarder_address = self._get_config()['forwarder']
        pan_token_address = self._get_config()['pan_token']
        domain_data = self.__get_eip712_domain_data()
        message_data = self.__get_transfer_to_message_data(
            request.source_blockchain, destination_blockchain,
            request.source_transfer_id, request.source_transaction_id,
            request.sender_address, request.recipient_address,
            request.source_token_address, request.destination_token_address,
            request.amount, request.validator_nonce, hub_address,
            forwarder_address, pan_token_address)
        signable_message = eth_account.messages.encode_typed_data(
            domain_data, _TRANSFER_TO_MESSAGE_TYPES, message_data)
        try:
            signer_address = web3.Account.recover_message(
                signable_message, signature=request.signature)
        except Exception:
            raise self._create_error('unable to recover the signer\'s address',
                                     request=request)
        return BlockchainAddress(signer_address)

    def sign_transfer_to_message(
            self,
            request: BlockchainClient.TransferToMessageSignRequest) -> str:
        # Docstring inherited
        if (request.incoming_transfer.eventual_destination_blockchain
                != self.get_blockchain()):
            raise self._create_error(
                'eventual destination blockchain of incoming transfer must be '
                f'{self.get_blockchain_name()}', request=request)
        try:
            assert request.destination_hub_address == self._get_config()['hub']
            assert (request.destination_forwarder_address ==
                    self._get_config()['forwarder'])
            pan_token_address = self._get_config()['pan_token']
            domain_data = self.__get_eip712_domain_data()
            message_data = self.__get_transfer_to_message_data(
                request.incoming_transfer.source_blockchain,
                request.incoming_transfer.eventual_destination_blockchain,
                request.incoming_transfer.source_transfer_id,
                request.incoming_transfer.source_transaction_id,
                request.incoming_transfer.sender_address,
                request.incoming_transfer.eventual_recipient_address,
                request.incoming_transfer.source_token_address,
                request.incoming_transfer.eventual_destination_token_address,
                request.incoming_transfer.amount, request.validator_nonce,
                request.destination_hub_address,
                request.destination_forwarder_address, pan_token_address)
            signed_message = web3.Account.sign_typed_data(
                self.__private_key, domain_data, _TRANSFER_TO_MESSAGE_TYPES,
                message_data)
            return signed_message.signature.to_0x_hex()
        except Exception:
            raise self._create_error('unable to sign a transferTo message',
                                     request=request)

    def start_transfer_to_submission(
            self, request: BlockchainClient.TransferToSubmissionStartRequest) \
            -> uuid.UUID:
        # Docstring inherited
        if (request.incoming_transfer.eventual_destination_blockchain
                != self.get_blockchain()):
            raise self._create_error(
                'eventual destination blockchain of incoming transfer must be '
                f'{self.get_blockchain_name()}', request=request)
        try:
            node_connections = self.__create_node_connections()
            hub_contract = self._create_hub_contract(node_connections)
            on_chain_request: _OnChainTransferToRequest = (
                request.incoming_transfer.source_blockchain.value,
                request.incoming_transfer.source_transfer_id,
                request.incoming_transfer.source_transaction_id,
                request.incoming_transfer.sender_address,
                request.incoming_transfer.eventual_recipient_address,
                request.incoming_transfer.source_token_address,
                request.incoming_transfer.eventual_destination_token_address,
                request.incoming_transfer.amount, request.validator_nonce)
            sorted_signer_addresses, sorted_signatures = \
                self.__sort_validator_node_signatures(
                    request.validator_node_signatures)
            self.__verify_transfer_to_request(hub_contract,
                                              request.incoming_transfer,
                                              on_chain_request,
                                              sorted_signer_addresses,
                                              sorted_signatures)
            internal_transaction_id = self.__submit_transfer_to_request(
                node_connections, request.internal_transfer_id,
                on_chain_request, sorted_signer_addresses, sorted_signatures)
            return internal_transaction_id
        except ResultsNotMatchingError:
            raise
        except EthereumClientError:
            raise
        except Exception:
            raise self._create_error('unable to start a transferTo submission',
                                     request=request)

    def _create_forwarder_contract(
            self, node_connections: NodeConnections) -> _Contract:
        forwarder_address = BlockchainAddress(self._get_config()['forwarder'])
        return self.get_utilities().create_contract(
            forwarder_address, self._versioned_pantos_forwarder_abi,
            node_connections)

    def _create_hub_contract(
            self, node_connections: NodeConnections,
            hub_address: BlockchainAddress | None = None) -> _Contract:
        if hub_address is None:
            hub_address = BlockchainAddress(self._get_config()['hub'])
        return self.get_utilities().create_contract(
            hub_address, self._versioned_pantos_hub_abi, node_connections)

    def _create_token_contract(self, node_connections: NodeConnections,
                               token_address: BlockchainAddress) -> _Contract:
        return self.get_utilities().create_contract(
            token_address, self._versioned_pantos_token_abi, node_connections)

    def _read_transfer_to_transaction_data(
            self, transaction_id: str, read_destination_transfer_id: bool) \
            -> BlockchainClient._TransferToTransactionDataResponse:
        try:
            node_connections = self.__create_node_connections()
            transaction_receipt = node_connections.eth.get_transaction_receipt(
                typing.cast(web3.types.HexStr, transaction_id)).get()
            _logger.info('transferTo transaction receipt', extra=json.loads(
                web3.Web3.to_json(transaction_receipt)))  # type: ignore
            block_number = transaction_receipt['blockNumber']
            destination_transfer_id = None
            if read_destination_transfer_id:
                hub_contract = self._create_hub_contract(node_connections)
                event = hub_contract.events.TransferToSucceeded()
                event_log = event.process_receipt(
                    transaction_receipt, errors=web3.logs.DISCARD)[0].get()
                destination_transfer_id = event_log['args'][
                    'destinationTransferId']
            return BlockchainClient._TransferToTransactionDataResponse(
                block_number, destination_transfer_id=destination_transfer_id)
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read transferTo transaction data',
                transaction_id=transaction_id,
                read_destination_transfer_id=read_destination_transfer_id)

    def __create_outgoing_transfers(
            self, event_logs: typing.Iterable[web3.types.EventData],
            hub_contract_address: str) -> list[CrossChainTransfer]:
        outgoing_transfers: list[CrossChainTransfer] = []
        for event_log in event_logs:
            assert event_log['event'] == 'TransferFromSucceeded'
            # TransferFromSucceeded event arguments
            event_args = event_log['args']
            event_request = event_args['request']
            source_transfer_id = event_args['sourceTransferId']
            destination_blockchain_id = event_request[
                'destinationBlockchainId']
            sender_address = event_request['sender']
            recipient_address = event_request['recipient']
            source_token_address = event_request['sourceToken']
            destination_token_address = event_request['destinationToken']
            amount = event_request['amount']
            service_node_address = event_request['serviceNode']
            fee = event_request['fee']
            assert isinstance(source_transfer_id, int)
            assert isinstance(destination_blockchain_id, int)
            assert isinstance(sender_address, str)
            assert isinstance(recipient_address, str)
            assert isinstance(source_token_address, str)
            assert isinstance(destination_token_address, str)
            assert isinstance(amount, int)
            assert isinstance(service_node_address, str)
            assert isinstance(fee, int)
            # Transaction and block data
            transaction_hash = event_log['transactionHash'].to_0x_hex()
            block_number = event_log['blockNumber']
            block_hash = event_log['blockHash'].to_0x_hex()
            assert isinstance(transaction_hash, str)
            assert isinstance(block_number, int)
            assert isinstance(block_hash, str)
            source_blockchain = self.get_blockchain()
            destination_blockchain = Blockchain(destination_blockchain_id)
            assert source_blockchain != destination_blockchain
            outgoing_transfer = CrossChainTransfer(
                source_blockchain, destination_blockchain,
                BlockchainAddress(hub_contract_address), source_transfer_id,
                transaction_hash, block_number, block_hash,
                BlockchainAddress(sender_address),
                BlockchainAddress(recipient_address),
                BlockchainAddress(source_token_address),
                BlockchainAddress(destination_token_address), amount, fee,
                BlockchainAddress(service_node_address))
            outgoing_transfers.append(outgoing_transfer)
        return outgoing_transfers

    def __create_node_connections(self) -> NodeConnections:
        provider_timeout = self._get_config()['provider_timeout']
        return self.get_utilities().create_node_connections(provider_timeout)

    def __get_blockchain_nodes_domains(
            self, node_connections: NodeConnections) -> str:
        blockchain_nodes_domains: list[str] = []
        configured_node_connections: list[web3.Web3] = \
            node_connections.get_configured_node_connections()
        for node_connection in configured_node_connections:
            if not isinstance(node_connection.provider,
                              web3.providers.rpc.HTTPProvider):
                continue
            blockchain_node_domain = urllib.parse.urlparse(
                node_connection.provider.endpoint_uri).netloc
            assert isinstance(blockchain_node_domain, str)
            blockchain_nodes_domains.append(blockchain_node_domain)
        return ', '.join(blockchain_nodes_domains)

    def __get_eip712_domain_data(self) -> dict[str, typing.Any]:
        return {
            'name': _EIP712_DOMAIN_NAME,
            'version': str(self.protocol_version.major),
            'chainId': self._get_config()['chain_id'],
            'verifyingContract': self._get_config()['forwarder']
        }

    def __get_nonce(self, node_connections: NodeConnections,
                    internal_transfer_id: int) -> int:
        transaction_count = node_connections.eth.get_transaction_count(
            self.__address).get_maximum_result()
        database_access.update_transfer_nonce(internal_transfer_id,
                                              self.get_blockchain(),
                                              transaction_count)
        nonce = database_access.read_transfer_nonce(internal_transfer_id)
        assert nonce is not None
        return nonce

    def __get_transfer_to_message_data(
            self, source_blockchain: Blockchain,
            destination_blockchain: Blockchain, source_transfer_id: int,
            source_transaction_id: str, sender_address: BlockchainAddress,
            recipient_address: BlockchainAddress,
            source_token_address: BlockchainAddress,
            destination_token_address: BlockchainAddress, amount: int,
            validator_nonce: int, hub_address: str, forwarder_address: str,
            pan_token_address: str) -> dict[str, typing.Any]:
        return {
            'request': {
                'sourceBlockchainId': source_blockchain.value,
                'sourceTransferId': source_transfer_id,
                'sourceTransactionId': source_transaction_id,
                'sender': sender_address,
                'recipient': recipient_address,
                'sourceToken': source_token_address,
                'destinationToken': destination_token_address,
                'amount': amount,
                'nonce': validator_nonce
            },
            'destinationBlockchainId': destination_blockchain.value,
            'pantosHub': hub_address,
            'pantosForwarder': forwarder_address,
            'pantosToken': pan_token_address
        }

    def __sort_validator_node_signatures(
            self, validator_node_signatures: dict[BlockchainAddress, str]) \
            -> tuple[list[BlockchainAddress], list[str]]:
        sorted_signer_addresses = sorted(
            validator_node_signatures,
            key=lambda signer_address: int(signer_address, 16))
        sorted_signatures = [
            validator_node_signatures[signer_address]
            for signer_address in sorted_signer_addresses
        ]
        return sorted_signer_addresses, sorted_signatures

    def __submit_transfer_to_request(
            self, node_connections: NodeConnections, internal_transfer_id: int,
            on_chain_request: _OnChainTransferToRequest,
            sorted_signer_addresses: list[BlockchainAddress],
            sorted_signatures: list[str]) -> uuid.UUID:
        contract_address = self._get_config()['hub']
        versioned_contract_abi = self._versioned_pantos_hub_abi
        function_selector = _HUB_TRANSFER_TO_FUNCTION_SELECTOR
        function_args = (on_chain_request, sorted_signer_addresses,
                         sorted_signatures)
        gas = (_HUB_TRANSFER_TO_BASE_GAS +
               len(sorted_signer_addresses) * _HUB_TRANSFER_TO_GAS_PER_SIGNER)
        min_adaptable_fee_per_gas = \
            self._get_config()['min_adaptable_fee_per_gas']
        max_total_fee_per_gas = self._get_config().get('max_total_fee_per_gas')
        if max_total_fee_per_gas == 0:
            max_total_fee_per_gas = None
        amount = None
        nonce = self.__get_nonce(node_connections, internal_transfer_id)
        adaptable_fee_increase_factor = \
            self._get_config()['adaptable_fee_increase_factor']
        blocks_until_resubmission = \
            self._get_config()['blocks_until_resubmission']
        request = BlockchainUtilities.TransactionSubmissionStartRequest(
            contract_address, versioned_contract_abi, function_selector,
            function_args, gas, min_adaptable_fee_per_gas,
            max_total_fee_per_gas, amount, nonce,
            adaptable_fee_increase_factor, blocks_until_resubmission)
        try:
            return self.get_utilities().start_transaction_submission(
                request, node_connections)
        except (TransactionNonceTooLowError, TransactionUnderpricedError):
            database_access.reset_transfer_nonce(internal_transfer_id)
            raise

    def __verify_transfer_to_request(
            self, hub_contract: _Contract,
            incoming_transfer: CrossChainTransfer,
            on_chain_request: _OnChainTransferToRequest,
            sorted_signer_addresses: list[BlockchainAddress],
            sorted_signatures: list[str]) -> None:
        try:
            hub_contract.functions.verifyTransferTo(
                on_chain_request, sorted_signer_addresses,
                sorted_signatures).call().get()
        except web3.exceptions.ContractLogicError as error:
            if _NON_MATCHING_FORWARDER_ERROR in str(error):
                raise self._create_non_matching_forwarder_error(
                    source_blockchain=incoming_transfer.source_blockchain,
                    source_transaction_id=incoming_transfer.
                    source_transaction_id,
                    destination_token_address=incoming_transfer.
                    destination_token_address)
            if _SOURCE_TRANSFER_ID_ALREADY_USED_ERROR in str(error):
                raise self._create_source_transfer_id_already_used_error(
                    source_blockchain=incoming_transfer.source_blockchain,
                    source_transfer_id=incoming_transfer.source_transfer_id,
                    source_transaction_id=incoming_transfer.
                    source_transaction_id)
            raise
