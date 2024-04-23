"""Module that defines entities to be used across application layers.

"""
import dataclasses
import typing

from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

CrossChainTransferDict = dict[str, typing.Union[int, str]]
"""Type of a Pantos cross-chain transfer dictionary."""


@dataclasses.dataclass
class CrossChainTransfer:
    """Representation of a Pantos cross-chain transfer.

    Attributes
    ----------
    source_blockchain : Blockchain
        The transfer's source blockchain.
    destination_blockchain : Blockchain
        The transfer's destination blockchain.
    source_hub_address : BlockchainAddress
        The address of the Pantos Hub contract on the source blockchain.
    source_transfer_id : int
        The Pantos transfer ID on the source blockchain.
    source_transaction_id : str
        The transfer's transaction ID/hash on the source blockchain.
    source_block_number : int
        The number of the transfer transaction's block on the source
        blockchain.
    source_block_hash : str
        The hash of the transfer transaction's block on the source
        blockchain.
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
    fee : int
        The total fee for the transfer (in paninis).
    service_node_address : BlockchainAddress
        The address of the submitting Service Node on the source
        blockchain.
    is_reversal_transfer : bool
        True if the cross-chain transfer is reversed, i.e. the amount of
        tokens is returned to the sender on the source blockchain
        (default: False).

    """
    source_blockchain: Blockchain
    destination_blockchain: Blockchain
    source_hub_address: BlockchainAddress
    source_transfer_id: int
    source_transaction_id: str
    source_block_number: int
    source_block_hash: str
    sender_address: BlockchainAddress
    recipient_address: BlockchainAddress
    source_token_address: BlockchainAddress
    destination_token_address: BlockchainAddress
    amount: int
    fee: int
    service_node_address: BlockchainAddress
    is_reversal_transfer: bool = False

    @property
    def eventual_destination_blockchain(self) -> Blockchain:
        """The eventual destination blockchain after the cross-chain
        transfer has been validated.

        """
        return (self.source_blockchain
                if self.is_reversal_transfer else self.destination_blockchain)

    @property
    def eventual_recipient_address(self) -> BlockchainAddress:
        """The eventual recipient address after the cross-chain transfer
        has been validated.

        """
        return (self.sender_address
                if self.is_reversal_transfer else self.recipient_address)

    @property
    def eventual_destination_token_address(self) -> BlockchainAddress:
        """The eventual destination token address after the cross-chain
        transfer has been validated.

        """
        return (self.source_token_address if self.is_reversal_transfer else
                self.destination_token_address)

    def to_dict(self) -> CrossChainTransferDict:
        """Convert the cross-chain transfer instance to a dictionary.

        Returns
        -------
        CrossChainTransferDict
            The dictionary representation of the cross-chain transfer.

        """
        return {
            'source_blockchain_id': self.source_blockchain.value,
            'destination_blockchain_id': self.destination_blockchain.value,
            'source_hub_address': self.source_hub_address,
            'source_transfer_id': self.source_transfer_id,
            'source_transaction_id': self.source_transaction_id,
            'source_block_number': self.source_block_number,
            'source_block_hash': self.source_block_hash,
            'sender_address': self.sender_address,
            'recipient_address': self.recipient_address,
            'source_token_address': self.source_token_address,
            'destination_token_address': self.destination_token_address,
            'amount': self.amount,
            'fee': self.fee,
            'service_node_address': self.service_node_address,
            'is_reversal_transfer': self.is_reversal_transfer
        }

    @staticmethod
    def from_dict(dict_: CrossChainTransferDict) -> 'CrossChainTransfer':
        """Create a cross-chain transfer instance from its dictionary
        representation.

        Parameters
        ----------
        dict_ : CrossChainTransferDict
            The dictionary representation of the cross-chain transfer.

        Returns
        -------
        CrossChainTransfer
            The created cross-chain transfer instance.

        """
        source_blockchain_id = dict_['source_blockchain_id']
        assert isinstance(source_blockchain_id, int)
        destination_blockchain_id = dict_['destination_blockchain_id']
        assert isinstance(destination_blockchain_id, int)
        source_hub_address = dict_['source_hub_address']
        assert isinstance(source_hub_address, str)
        source_transfer_id = dict_['source_transfer_id']
        assert isinstance(source_transfer_id, int)
        source_transaction_id = dict_['source_transaction_id']
        assert isinstance(source_transaction_id, str)
        source_block_number = dict_['source_block_number']
        assert isinstance(source_block_number, int)
        source_block_hash = dict_['source_block_hash']
        assert isinstance(source_block_hash, str)
        sender_address = dict_['sender_address']
        assert isinstance(sender_address, str)
        recipient_address = dict_['recipient_address']
        assert isinstance(recipient_address, str)
        source_token_address = dict_['source_token_address']
        assert isinstance(source_token_address, str)
        destination_token_address = dict_['destination_token_address']
        assert isinstance(destination_token_address, str)
        amount = dict_['amount']
        assert isinstance(amount, int)
        fee = dict_['fee']
        assert isinstance(fee, int)
        service_node_address = dict_['service_node_address']
        assert isinstance(service_node_address, str)
        is_reversal_transfer = dict_['is_reversal_transfer']
        assert isinstance(is_reversal_transfer, bool)
        return CrossChainTransfer(Blockchain(source_blockchain_id),
                                  Blockchain(destination_blockchain_id),
                                  BlockchainAddress(source_hub_address),
                                  source_transfer_id, source_transaction_id,
                                  source_block_number, source_block_hash,
                                  BlockchainAddress(sender_address),
                                  BlockchainAddress(recipient_address),
                                  BlockchainAddress(source_token_address),
                                  BlockchainAddress(destination_token_address),
                                  amount, fee,
                                  BlockchainAddress(service_node_address),
                                  is_reversal_transfer)
