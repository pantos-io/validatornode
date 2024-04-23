"""Module that defines database-specific exceptions.

"""
import typing

from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.exceptions import ValidatorNodeError


class DatabaseError(ValidatorNodeError):
    """Base exception class for all database errors.

    """
    pass


class ValidatorNonceNotUniqueError(DatabaseError):
    """Error that is raised when an already existing validator nonce is
    requested to be added again for a specific blockchain.

    """
    def __init__(self, blockchain: Blockchain, validator_nonce: int,
                 **kwargs: typing.Any):
        """Construct an error instance.

        Parameters
        ----------
        blockchain : Blockchain
            The affected blockchain.
        validator_nonce : int
            The non-unique validator nonce.
        **kwargs : dict
            Additional information about the error as keyword arguments.

        """
        super().__init__('validator nonce not unique', blockchain=blockchain,
                         validator_nonce=validator_nonce, **kwargs)
