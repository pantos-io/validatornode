"""Base classes for all business logic interactors and errors.

"""
import typing

from pantos.common.exceptions import ErrorCreator

from pantos.validatornode.configuration import config
from pantos.validatornode.exceptions import ValidatorNodeError


class InteractorError(ValidatorNodeError):
    """Base exception class for all interactor errors.

    """
    pass


class DuplicateSignatureError(InteractorError):
    """Exception to be raised if there is a duplicate signature.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('duplicate signature', **kwargs)


class InvalidSignatureError(InteractorError):
    """Exception to be raised if a signature is invalid.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('invalid signature', **kwargs)


class InvalidSignerError(InteractorError):
    """Exception to be raised if a signer is invalid.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('invalid signer', **kwargs)


class UnknownTransferError(InteractorError):
    """Exception to be raised if a transfer is unknown.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('unknown transfer', **kwargs)


class Interactor(ErrorCreator[InteractorError]):
    """Base class for all interactors.

    """
    def _create_duplicate_signature_error(
            self, **kwargs: typing.Any) -> InteractorError:
        return self._create_error(
            specialized_error_class=DuplicateSignatureError, **kwargs)

    def _create_invalid_signature_error(
            self, **kwargs: typing.Any) -> InteractorError:
        return self._create_error(
            specialized_error_class=InvalidSignatureError, **kwargs)

    def _create_invalid_signer_error(self,
                                     **kwargs: typing.Any) -> InteractorError:
        return self._create_error(specialized_error_class=InvalidSignerError,
                                  **kwargs)

    def _create_unknown_transfer_error(
            self, **kwargs: typing.Any) -> InteractorError:
        return self._create_error(specialized_error_class=UnknownTransferError,
                                  **kwargs)

    def _is_primary_node(self) -> bool:
        return config['application']['mode'] == 'primary'
