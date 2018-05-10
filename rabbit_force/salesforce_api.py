"""Salesforce REST API client definitions"""
from http import HTTPStatus as Status
import asyncio

import aiohttp

from . import exceptions as exc

#: Salesforce REST API version
API_VERSION = 42.0


class SalesforceApi:
    """Salesforce REST API client"""

    #: Map for associating HTTP status codes with exception types
    _ERROR_MAP = {
        Status.MULTIPLE_CHOICES: exc.SalesforceMultipleChoicesError,
        Status.NOT_MODIFIED: exc.SalesforceNotModifiedError,
        Status.BAD_REQUEST: exc.SalesforceBadRequestError,
        Status.UNAUTHORIZED: exc.SalesforceUnauthorizedError,
        Status.FORBIDDEN: exc.SalesforceForbiddenError,
        Status.NOT_FOUND: exc.SalesforceNotFoundError,
        Status.METHOD_NOT_ALLOWED: exc.SalesforceMethodNotAllowedError,
        Status.UNSUPPORTED_MEDIA_TYPE: exc.SalesforceUnsupportedMediaTypeError,
        Status.INTERNAL_SERVER_ERROR: exc.SalesforceInternalServerError
    }
    #: Timeout to give to HTTP _session to close itself
    _HTTP_SESSION_CLOSE_TIMEOUT = 0.250

    def __init__(self, authenticator):
        """
        :param aiosfstream.AuthenticatorBase authenticator: An authenticatior \
        object
        """
        #: Authenticator object for providing access tokens
        self.authenticator = authenticator
        #: HTTP session object
        self._session = None
        #: The API's base url
        self._base_url = None

    async def _get_http_session(self):
        """Factory method for getting the current HTTP session

        :return: The current session if it's not None, otherwise it creates a
                 new session.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_base_url(self):
        """Returns the API's base url"""
        if self._base_url is None:
            await self.authenticator.authenticate()
            self._base_url = f"{self.authenticator.instance_url}/services" \
                             f"/data/v{API_VERSION}/"
        return self._base_url

    async def _raise_error(self, response):
        """Raise the appropriate error for the status code of the *response*

        :param aiohttp.ClientResponse response: A response object
        :raise SalesforceMultipleChoicesError: For status \
        :obj:`~http.HTTPStatus.MULTIPLE_CHOICES`
        :raise SalesforceNotModifiedError: For status \
        :obj:`~http.HTTPStatus.NOT_MODIFIED`
        :raise SalesforceBadRequestError: For status \
        :obj:`~http.HTTPStatus.BAD_REQUEST`
        :raise SalesforceUnauthorizedError: For status \
        :obj:`~http.HTTPStatus.UNAUTHORIZED`
        :raise SalesforceForbiddenError: For status \
        :obj:`~http.HTTPStatus.FORBIDDEN`
        :raise SalesforceNotFoundError: For status \
        :obj:`~http.HTTPStatus.NOT_FOUND`
        :raise SalesforceMethodNotAllowedError: For status \
        :obj:`~http.HTTPStatus.METHOD_NOT_ALLOWED`
        :raise SalesforceUnsupportedMediaTypeError: For status \
        :obj:`~http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE`
        :raise SalesforceInternalServerError: For status \
        :obj:`~http.HTTPStatus.INTERNAL_SERVER_ERROR`
        :raise SalesforceRestError: For all other statuses
        """
        try:
            content = await response.json()
        except aiohttp.ContentTypeError:
            content = await response.text()

        error_cls = self._ERROR_MAP.get(response.status,
                                        exc.SalesforceRestError)

        raise error_cls(content)

    async def _verify_response(self, response):
        """Verify the status code of the *response* and raise the \
        appropriate error on failure

        :param aiohttp.ClientResponse response: A response object
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        if response.status >= Status.MULTIPLE_CHOICES:
            await self._raise_error(response)

    async def _request(self, method, path, json=None, params=None):
        """Send an HTTP request with the given *method* to the url defined by \
        *path*

        :param str method: An HTTP method
        :param str path: A path relative to the API's base url
        :param json: Data to send in the body of the request, serialize as \
        JSON
        :type json: dict or None
        :param params: URL parameters and their values
        :type params: dict or None
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        # get a session object
        session = await self._get_http_session()
        # form the final absolute url of the request
        url = await self._get_base_url() + path
        # create the authorization header
        auth_header_value = (self.authenticator.token_type + " " +
                             self.authenticator.access_token)
        headers = {"Authorization": auth_header_value}

        # send the request
        try:
            response = await session.request(method,
                                             url,
                                             params=params,
                                             json=json,
                                             headers=headers)
        # on a client error raise a network error
        except aiohttp.ClientError as error:
            raise exc.NetworkError(str(error)) from error

        # verify that the request was successful, otherwise raise an error
        await self._verify_response(response)

        # return the data returned by the server
        try:
            return await response.json()
        # if the returned response data is not JSON then return None
        except aiohttp.ContentTypeError:
            return None

    async def _request_with_retry(self, method, path, json=None, params=None):
        """Send an HTTP request with the given *method* to the url defined by \
        *path*

        If the request fails with an SalesforceUnauthorizedError, then the
        request will be resent after a re-authentication

        :param str method: An HTTP method
        :param str path: A path relative to the API's base url
        :param json: Data to send in the body of the request, serialize as \
        JSON
        :type json: dict or None
        :param params: URL parameters and their values
        :type params: dict or None
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        try:
            return await self._request(method, path, json, params)
        except exc.SalesforceUnauthorizedError:
            await self.authenticator.authenticate()
            return await self._request(method, path, json, params)

    @staticmethod
    def _resource_path(resource_name, record_id=None):
        """Get the relative path of the resource

        :param str resource_name: The name of the resource type
        :param record_id: An optional id value. If specified, then given \
        resource's subpath will be returned
        :type record_id: str or None
        :return: The relative path of the resource
        :rtype: str
        """
        path = f"sobjects/{resource_name}/"
        if record_id:
            path += record_id
        return path

    async def close(self):
        """Close the client"""
        # graceful shutdown recommended by the documentation
        # https://aiohttp.readthedocs.io/en/stable/client_advanced.html\
        # #graceful-shutdown
        await self._session.close()
        await asyncio.sleep(self._HTTP_SESSION_CLOSE_TIMEOUT)

    async def query(self, query):
        """Executes the specified SOQL *query*

        :param query:
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        return await self._request_with_retry("GET", "query",
                                              params={"q": query})

    async def create(self, resource_name, data):
        """Creates a resource for the fields specified in *data*

        :param str resource_name: The name of the resource type
        :param dict data: Field values
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        path = self._resource_path(resource_name)
        return await self._request_with_retry("POST", path, json=data)

    async def update(self, resource_name, record_id, data):
        """Updates the resource with the specified *record_id* with the fields
        specified in *data*

        :param str resource_name: The name of the resource type
        :param str record_id: The id of the resource
        :param dict data: Field values
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        path = self._resource_path(resource_name, record_id)
        return await self._request_with_retry("PATCH", path, json=data)

    async def delete(self, resource_name, record_id):
        """Deletes the resource with the specified *record_id*

        :param str resource_name: The name of the resource type
        :param str record_id: The id of the resource
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        path = self._resource_path(resource_name, record_id)
        return await self._request_with_retry("DELETE", path)

    async def get(self, resource_name, record_id):
        """Returns the resource with the specified *record_id*

        :param str resource_name: The name of the resource type
        :param str record_id: The id of the resource
        :return: The data returned by the server
        :rtype: dict or None
        :raise NetworkError: If the request fails due to a network failure
        :raise SalesforceRestError: If the status code of the response marks \
        a failure
        """
        path = self._resource_path(resource_name, record_id)
        return await self._request_with_retry("GET", path)
