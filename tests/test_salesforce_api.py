from http import HTTPStatus

from asynctest import TestCase, mock
import aiohttp

from rabbit_force.salesforce_api import SalesforceApi, API_VERSION
from rabbit_force.exceptions import SalesforceRestError, NetworkError, \
    SalesforceUnauthorizedError


class TestSalesforceApi(TestCase):
    def setUp(self):
        self.auth = mock.MagicMock()
        self.auth.authenticate = mock.CoroutineMock()
        self.api = SalesforceApi(self.auth, loop=self.loop)

    async def test_get_http_session(self):
        self.api._session = mock.MagicMock()
        self.api._session.closed = False

        result = await self.api._get_http_session()

        self.assertIs(result, self.api._session)

    @mock.patch("rabbit_force.salesforce_api.aiohttp.ClientSession")
    async def test_get_http_session_creates_session(self, session_cls):
        self.api._session = None

        result = await self.api._get_http_session()

        self.assertIs(result, session_cls.return_value)
        session_cls.assert_called_with(loop=self.loop)

    @mock.patch("rabbit_force.salesforce_api.aiohttp.ClientSession")
    async def test_get_http_session_creates_session_if_closed(
            self, session_cls):
        self.api._session = mock.MagicMock()
        self.api._session.closed = True

        result = await self.api._get_http_session()

        self.assertIs(result, session_cls.return_value)
        session_cls.assert_called_with(loop=self.loop)

    async def test_get_base_url(self):
        self.api._base_url = "url"

        result = await self.api._get_base_url()

        self.assertIs(result, self.api._base_url)

    async def test_get_base_url_creates_base_url(self):
        self.auth.instance_url = "instance_url"

        result = await self.api._get_base_url()

        self.assertEqual(result,
                         f"{self.auth.instance_url}/services"
                         f"/data/v{API_VERSION}/")
        self.auth.authenticate.assert_not_called()

    async def test_get_base_url_creates_base_url_not_authenticated(self):
        self.auth.instance_url = None

        result = await self.api._get_base_url()

        self.assertEqual(result,
                         f"{self.auth.instance_url}/services"
                         f"/data/v{API_VERSION}/")
        self.auth.authenticate.assert_called()

    async def test_raise_error_from_error_map(self):
        self.assertIn(HTTPStatus.NOT_FOUND, self.api._ERROR_MAP)
        response = mock.MagicMock()
        content = "content"
        response.json = mock.CoroutineMock(return_value=content)
        response.status = HTTPStatus.NOT_FOUND

        with self.assertRaisesRegex(self.api._ERROR_MAP[HTTPStatus.NOT_FOUND],
                                    content):
            await self.api._raise_error(response)

    async def test_raise_error_from_error_map_on_json_error(self):
        self.assertIn(HTTPStatus.NOT_FOUND, self.api._ERROR_MAP)
        response = mock.MagicMock()
        content = "content"
        response.json = mock.CoroutineMock(
            side_effect=aiohttp.ContentTypeError(None, None)
        )
        response.status = HTTPStatus.NOT_FOUND
        response.text = mock.CoroutineMock(return_value=content)

        with self.assertRaisesRegex(self.api._ERROR_MAP[HTTPStatus.NOT_FOUND],
                                    content):
            await self.api._raise_error(response)

    async def test_raise_error_general_error(self):
        self.assertNotIn(HTTPStatus.TOO_MANY_REQUESTS, self.api._ERROR_MAP)
        response = mock.MagicMock()
        content = "content"
        response.json = mock.CoroutineMock(return_value=content)
        response.status = HTTPStatus.TOO_MANY_REQUESTS

        with self.assertRaisesRegex(SalesforceRestError,
                                    content):
            await self.api._raise_error(response)

    async def test_raise_error_general_error_on_json_error(self):
        self.assertNotIn(HTTPStatus.TOO_MANY_REQUESTS, self.api._ERROR_MAP)
        response = mock.MagicMock()
        content = "content"
        response.json = mock.CoroutineMock(
            side_effect=aiohttp.ContentTypeError(None, None)
        )
        response.status = HTTPStatus.TOO_MANY_REQUESTS
        response.text = mock.CoroutineMock(return_value=content)

        with self.assertRaisesRegex(SalesforceRestError,
                                    content):
            await self.api._raise_error(response)

    async def test_request(self):
        self.auth.token_type = "type"
        self.auth.access_token = "token"
        base_url = "base_url"
        response_data = object()
        response = mock.MagicMock()
        response.json = mock.CoroutineMock(return_value=response_data)
        session = mock.MagicMock()
        session.request = mock.CoroutineMock(return_value=response)
        self.api._get_http_session = mock.CoroutineMock(return_value=session)
        self.api._get_base_url = mock.CoroutineMock(return_value=base_url)
        self.api._verify_response = mock.CoroutineMock()
        method = "method"
        path = "path"
        json = object()
        params = object()
        auth_header = self.auth.token_type + " " + self.auth.access_token
        expected_headers = {"Authorization": auth_header}

        result = await self.api._request(method,
                                         path,
                                         json=json,
                                         params=params)

        self.assertEqual(result, response_data)
        session.request.assert_called_with(method,
                                           base_url + path,
                                           json=json,
                                           params=params,
                                           headers=expected_headers)
        self.api._verify_response.assert_called_with(response)

    async def test_request_client_error(self):
        self.auth.token_type = "type"
        self.auth.access_token = "token"
        base_url = "base_url"
        response_data = object()
        response = mock.MagicMock()
        response.json = mock.CoroutineMock(return_value=response_data)
        session = mock.MagicMock()
        error = aiohttp.ClientError("error")
        session.request = mock.CoroutineMock(side_effect=error)
        self.api._get_http_session = mock.CoroutineMock(return_value=session)
        self.api._get_base_url = mock.CoroutineMock(return_value=base_url)
        self.api._verify_response = mock.CoroutineMock()
        method = "method"
        path = "path"
        json = object()
        params = object()
        auth_header = self.auth.token_type + " " + self.auth.access_token
        expected_headers = {"Authorization": auth_header}

        with self.assertRaisesRegex(NetworkError, str(error)):
            await self.api._request(method,
                                    path,
                                    json=json,
                                    params=params)

        session.request.assert_called_with(method,
                                           base_url + path,
                                           json=json,
                                           params=params,
                                           headers=expected_headers)

    async def test_request_content_error(self):
        self.auth.token_type = "type"
        self.auth.access_token = "token"
        base_url = "base_url"
        response = mock.MagicMock()
        error = aiohttp.ContentTypeError(None, None)
        response.json = mock.CoroutineMock(side_effect=error)
        session = mock.MagicMock()
        session.request = mock.CoroutineMock(return_value=response)
        self.api._get_http_session = mock.CoroutineMock(return_value=session)
        self.api._get_base_url = mock.CoroutineMock(return_value=base_url)
        self.api._verify_response = mock.CoroutineMock()
        method = "method"
        path = "path"
        json = object()
        params = object()
        auth_header = self.auth.token_type + " " + self.auth.access_token
        expected_headers = {"Authorization": auth_header}

        result = await self.api._request(method,
                                         path,
                                         json=json,
                                         params=params)

        self.assertIsNone(result)
        session.request.assert_called_with(method,
                                           base_url + path,
                                           json=json,
                                           params=params,
                                           headers=expected_headers)
        self.api._verify_response.assert_called_with(response)

    async def test_request_with_retry(self):
        response_data = object()
        self.api._request = mock.CoroutineMock(return_value=response_data)
        method = "method"
        path = "path"
        json = object()
        params = object()

        result = await self.api._request_with_retry(method,
                                                    path,
                                                    json=json,
                                                    params=params)

        self.assertIs(result, response_data)
        self.api._request.assert_called_with(method, path, json, params)

    async def test_request_with_retry_auth_error(self):
        response_data = object()
        error = SalesforceUnauthorizedError()
        self.api._request = mock.CoroutineMock(side_effect=[error,
                                                            response_data])
        method = "method"
        path = "path"
        json = object()
        params = object()

        result = await self.api._request_with_retry(method,
                                                    path,
                                                    json=json,
                                                    params=params)

        self.assertIs(result, response_data)
        self.api._request.assert_has_calls([
            mock.call(method, path, json, params),
            mock.call(method, path, json, params)
        ])
        self.auth.authenticate.assert_called()

    async def test_request_with_retry_double_auth_error(self):
        error = SalesforceUnauthorizedError()
        self.api._request = mock.CoroutineMock(side_effect=[error, error])
        method = "method"
        path = "path"
        json = object()
        params = object()

        with self.assertRaises(SalesforceUnauthorizedError):
            await self.api._request_with_retry(method,
                                               path,
                                               json=json,
                                               params=params)

        self.api._request.assert_has_calls([
            mock.call(method, path, json, params),
            mock.call(method, path, json, params)
        ])
        self.auth.authenticate.assert_called()

    def test_get_resource_path(self):
        resource_name = "name"
        resource_id = None

        result = self.api._resource_path(resource_name, resource_id)

        self.assertEqual(result, f"sobjects/{resource_name}/")

    def test_get_resource_path_with_id(self):
        resource_name = "name"
        resource_id = "id"

        result = self.api._resource_path(resource_name, resource_id)

        self.assertEqual(result, f"sobjects/{resource_name}/{resource_id}")

    @mock.patch("rabbit_force.salesforce_api.asyncio.sleep")
    async def test_close(self, sleep):
        self.api._session = mock.MagicMock()
        self.api._session.close = mock.CoroutineMock()

        await self.api.close()

        self.api._session.close.assert_called()
        sleep.assert_called_with(self.api._HTTP_SESSION_CLOSE_TIMEOUT)

    async def test_query(self):
        query = "query"
        response_data = object()
        self.api._request_with_retry = mock.CoroutineMock(
            return_value=response_data
        )

        result = await self.api.query(query)

        self.assertEqual(result, response_data)
        self.api._request_with_retry.assert_called_with("GET", "query",
                                                        params={"q": query})

    async def test_create(self):
        resource_name = "name"
        data = object()
        response_data = object()
        self.api._request_with_retry = mock.CoroutineMock(
            return_value=response_data
        )
        path = "path"
        self.api._resource_path = mock.MagicMock(return_value=path)

        result = await self.api.create(resource_name, data)

        self.assertEqual(result, response_data)
        self.api._resource_path.assert_called_with(resource_name)
        self.api._request_with_retry.assert_called_with("POST", path,
                                                        json=data)

    async def test_update(self):
        resource_name = "name"
        data = object()
        resource_id = object()
        response_data = object()
        self.api._request_with_retry = mock.CoroutineMock(
            return_value=response_data
        )
        path = "path"
        self.api._resource_path = mock.MagicMock(return_value=path)

        result = await self.api.update(resource_name, resource_id, data)

        self.assertEqual(result, response_data)
        self.api._resource_path.assert_called_with(resource_name,
                                                   resource_id)
        self.api._request_with_retry.assert_called_with("PATCH", path,
                                                        json=data)

    async def test_delete(self):
        resource_name = "name"
        resource_id = object()
        response_data = object()
        self.api._request_with_retry = mock.CoroutineMock(
            return_value=response_data
        )
        path = "path"
        self.api._resource_path = mock.MagicMock(return_value=path)

        result = await self.api.delete(resource_name, resource_id)

        self.assertEqual(result, response_data)
        self.api._resource_path.assert_called_with(resource_name,
                                                   resource_id)
        self.api._request_with_retry.assert_called_with("DELETE", path)

    async def test_get(self):
        resource_name = "name"
        resource_id = object()
        response_data = object()
        self.api._request_with_retry = mock.CoroutineMock(
            return_value=response_data
        )
        path = "path"
        self.api._resource_path = mock.MagicMock(return_value=path)

        result = await self.api.get(resource_name, resource_id)

        self.assertEqual(result, response_data)
        self.api._resource_path.assert_called_with(resource_name,
                                                   resource_id)
        self.api._request_with_retry.assert_called_with("GET", path)

    async def test_verify_response(self):
        response = mock.MagicMock()
        response.status = HTTPStatus.IM_USED
        self.api._raise_error = mock.CoroutineMock()

        await self.api._verify_response(response)

        self.api._raise_error.assert_not_called()

    async def test_verify_response_on_error(self):
        response = mock.MagicMock()
        response.status = HTTPStatus.MULTIPLE_CHOICES
        self.api._raise_error = mock.CoroutineMock()

        await self.api._verify_response(response)

        self.api._raise_error.assert_called_with(response)
