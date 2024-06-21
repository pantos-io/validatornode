"""Module for invoking the primary validator node's REST API from a
secondary validator node.

"""
import dataclasses
import logging
import typing

import requests
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.exceptions import ValidatorNodeError

_TRANSFER_SIGNATURE_RESOURCE = 'transfersignature'
_VALIDATOR_NONCE_RESOURCE = 'validatornonce'

_logger = logging.getLogger(__name__)


class PrimaryNodeClientError(ValidatorNodeError):
    """Exception to be raised for all errors caused by invoking the
    primary validator node's REST API.

    """
    pass


class PrimaryNodeDuplicateSignatureError(PrimaryNodeClientError):
    """Exception to be raised if the primary validator node reports a
    duplicate signature.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('duplicate signature', **kwargs)


class PrimaryNodeInvalidSignatureError(PrimaryNodeClientError):
    """Exception to be raised if the primary validator node reports an
    invalid signature.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('invalid signature', **kwargs)


class PrimaryNodeInvalidSignerError(PrimaryNodeClientError):
    """Exception to be raised if the primary validator node reports an
    invalid signer.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('invalid signer', **kwargs)


class PrimaryNodeUnknownTransferError(PrimaryNodeClientError):
    """Exception to be raised if the primary validator node reports an
    unknown transfer.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('unknown transfer', **kwargs)


class PrimaryNodeClient:
    """Client invoking the primary validator node's REST API.

    """
    def __init__(self, primary_node_url: str,
                 timeout: float | tuple[float, float] = 60):
        """Initialize a primary node client instance.

        Parameters
        ----------
        primary_node_url : str
            The URL of the primary validator node.
        timeout : float or tuple, optional
            The timeout for sending requests to the primary validator
            node given as either a pair of connect and read timeouts or
            just one timeout value to be applied to both (default: 60
            seconds).

        """
        self.__primary_node_url = primary_node_url
        if not primary_node_url.endswith('/'):
            self.__primary_node_url += '/'
        self.__timeout = timeout

    @dataclasses.dataclass
    class ValidatorNonceGetRequest:
        """Request data for getting the validator nonce for a
        cross-chain token transfer from the primary validator node.

        Attributes
        ----------
        source_blockchain : Blockchain
            The transfer's source blockchain.
        source_transaction_id : str
            The transfer's transaction ID/hash on the source blockchain.

        """
        source_blockchain: Blockchain
        source_transaction_id: str

    def get_validator_nonce(self, request: ValidatorNonceGetRequest) -> int:
        """Get the validator nonce for a cross-chain token transfer from
        the primary validator node.

        Parameters
        ----------
        request : ValidatorNonceGetRequest
            The request data.

        Returns
        -------
        int
            The validator nonce.

        Raises
        ------
        PrimaryNodeUnknownTransferError
            If the primary validator node does not know any transfer for
            the given source blockchain and transaction ID/hash.
        PrimaryNodeClientError
            If another error occurs during getting the validator nonce.

        """
        url = (f'{self.__primary_node_url}{_VALIDATOR_NONCE_RESOURCE}?'
               f'source_blockchain_id={request.source_blockchain.value}&'
               f'source_transaction_id={request.source_transaction_id}')
        extra_info = vars(request) | {'url': url, 'timeout': self.__timeout}
        response = self.__send_get_request(url, extra_info)
        extra_info |= {'status_code': response.status_code}
        json_response = self.__decode_json_response(response, extra_info)
        if response.status_code != requests.codes.ok:
            response_message = self.__extract_response_message(
                json_response, extra_info)
            if response.status_code == requests.codes.not_found:
                assert response_message is not None
                assert 'Unknown transfer.' in response_message
                raise PrimaryNodeUnknownTransferError(**extra_info)
            raise PrimaryNodeClientError('unable to get a validator nonce',
                                         **extra_info)
        validator_nonce = json_response.get('validator_nonce')
        assert isinstance(validator_nonce, int)
        return validator_nonce

    @dataclasses.dataclass
    class TransferSignaturePostRequest:
        """Request data for posting the signature for a cross-chain
        token transfer to the primary validator node.

        Attributes
        ----------
        source_blockchain : Blockchain
            The transfer's source blockchain.
        source_transaction_id : str
            The transfer's transaction ID/hash on the source blockchain.
        signature : str
            The transfer signature of the secondary validator node.

        """
        source_blockchain: Blockchain
        source_transaction_id: str
        signature: str

    def post_transfer_signature(self,
                                request: TransferSignaturePostRequest) -> None:
        """Post the signature for a cross-chain token transfer to the
        primary validator node.

        Parameters
        ----------
        request : TransferSignaturePostRequest
            The request data.

        Raises
        ------
        PrimaryNodeDuplicateSignatureError
            If the primary validator node reports the secondary
            validator node's transfer signature as already existing.
        PrimaryNodeInvalidSignatureError
            If the primary validator node reports the secondary
            validator node's transfer signature as being invalid.
        PrimaryNodeInvalidSignerError
            If the primary validator node reports the signer of the
            transfer signature as not being a validator node on the
            transfer's destination blockchain.
        PrimaryNodeUnknownTransferError
            If the primary validator node does not know any transfer for
            the given source blockchain and transaction ID/hash.
        PrimaryNodeClientError
            If another error occurs during posting the transfer
            signature.

        """
        url = (f'{self.__primary_node_url}{_TRANSFER_SIGNATURE_RESOURCE}')
        extra_info = vars(request) | {'url': url, 'timeout': self.__timeout}
        json_request = {
            'source_blockchain_id': request.source_blockchain.value,
            'source_transaction_id': request.source_transaction_id,
            'signature': request.signature
        }
        response = self.__send_post_request(url, json_request, extra_info)
        if response.status_code != requests.codes.no_content:
            extra_info |= {'status_code': response.status_code}
            json_response = self.__decode_json_response(response, extra_info)
            response_message = self.__extract_response_message(
                json_response, extra_info)
            if (response.status_code == requests.codes.bad_request
                    and response_message is not None
                    and 'Invalid signature.' in response_message):
                raise PrimaryNodeInvalidSignatureError(**extra_info)
            if response.status_code == requests.codes.conflict:
                assert response_message is not None
                assert 'Duplicate signature.' in response_message
                raise PrimaryNodeDuplicateSignatureError(**extra_info)
            if response.status_code == requests.codes.forbidden:
                assert response_message is not None
                assert 'Invalid signer.' in response_message
                raise PrimaryNodeInvalidSignerError(**extra_info)
            if response.status_code == requests.codes.not_found:
                assert response_message is not None
                assert 'Unknown transfer.' in response_message
                raise PrimaryNodeUnknownTransferError(**extra_info)
            raise PrimaryNodeClientError('unable to post a transfer signature',
                                         **extra_info)

    def __decode_json_response(self, response: requests.Response,
                               extra_info: dict[str, typing.Any]) -> dict:
        try:
            json_response = response.json()
        except requests.JSONDecodeError:
            raise PrimaryNodeClientError('JSON decode error', **extra_info)
        assert isinstance(json_response, dict)
        return json_response

    def __extract_response_message(
            self, json_response: dict,
            extra_info: dict[str, typing.Any]) -> str | None:
        response_message = json_response.get('message')
        if response_message is not None:
            assert isinstance(response_message, str)
            extra_info |= {'response_message': response_message}
        return response_message

    def __send_get_request(
            self, url: str, extra_info: dict[str,
                                             typing.Any]) -> requests.Response:
        _logger.info('new GET request', extra=extra_info)
        try:
            return requests.get(url, timeout=self.__timeout)
        except requests.Timeout:
            raise PrimaryNodeClientError('GET request timeout', **extra_info)
        except requests.RequestException:
            raise PrimaryNodeClientError('GET request error', **extra_info)

    def __send_post_request(
            self, url: str, json_request: dict[str, typing.Any],
            extra_info: dict[str, typing.Any]) -> requests.Response:
        _logger.info('new POST request', extra=extra_info)
        try:
            return requests.post(url, json=json_request,
                                 timeout=self.__timeout)
        except requests.Timeout:
            raise PrimaryNodeClientError('POST request timeout', **extra_info)
        except requests.RequestException:
            raise PrimaryNodeClientError('POST request error', **extra_info)
