from asynctest import TestCase, mock

from rabbit_force.salesforce_org import SalesforceOrg


class TestSalesforceOrg(TestCase):
    @mock.patch("rabbit_force.salesforce_org.PasswordAuthenticator")
    def setUp(self, auth_cls):
        self.authenticator = mock.MagicMock()
        self.authenticator.authenticate = mock.CoroutineMock()
        auth_cls.return_value = self.authenticator
        self.auth_cls = auth_cls

        self.consumer_key = "key"
        self.consumer_secret = "secret"
        self.username = "username"
        self.password = "password"

        self.org = SalesforceOrg(
            self.consumer_key,
            self.consumer_secret,
            self.username,
            self.password
        )

    def test_init(self):
        self.assertEqual(self.org.authenticator, self.authenticator)
        self.auth_cls.assert_called_with(
            self.consumer_key,
            self.consumer_secret,
            self.username,
            self.password
        )
        self.assertEqual(self.org.resources, {})
        self.assertIsNone(self.org._rest_client)

    @mock.patch("rabbit_force.salesforce_org.RestClient")
    async def test_get_client(self, rest_client_cls):
        self.authenticator._auth_response = {
            "access_token": "token"
        }

        result = await self.org._get_client()

        self.assertEqual(result, rest_client_cls.return_value)
        rest_client_cls.assert_called_with(
            instance_url=self.authenticator.instance_url,
            session_id=self.authenticator._auth_response["access_token"]
        )
        self.assertEqual(self.org._rest_client, result)

    async def test_get_client_existing_client(self):
        self.org._rest_client = object()

        result = await self.org._get_client()

        self.assertEqual(result, self.org._rest_client)

    @mock.patch("rabbit_force.salesforce_org.StreamingResourceFactory")
    async def test_add_resource(self, factory_cls):
        resource_type = object()
        resource_spec = object()
        factory = mock.MagicMock()
        factory_cls.return_value = factory
        durable = True
        self.org._get_client = mock.CoroutineMock()

        result = await self.org.add_resource(resource_type, resource_spec,
                                             durable)

        self.assertEqual(result, factory.get_resource.return_value)
        factory_cls.assert_called_with(
            resource_type,
            self.org._get_client.return_value
        )
        factory.get_resource.assert_called_with(resource_spec)
        self.assertEqual(result.durable, durable)
        self.assertEqual(self.org.resources[result.name], result)

    async def test_remove_resource(self):
        resource = mock.MagicMock()
        resource.type_name = "name"
        resource_client = mock.MagicMock()
        client = mock.MagicMock()
        client.name = resource_client
        self.org._get_client = mock.CoroutineMock(return_value=client)

        await self.org.remove_resource(resource)

        resource_client.delete.assert_called_with(resource.id)

    async def test_cleanup_resources(self):
        non_durable1 = mock.MagicMock()
        non_durable1.durable = False
        non_durable2 = mock.MagicMock()
        non_durable2.durable = False
        durable_resource = mock.MagicMock()
        durable_resource.durable = True
        self.org.resources = {
            "non_durable1": non_durable1,
            "non_durable2": non_durable2,
            "durable": durable_resource
        }
        self.org.remove_resource = mock.CoroutineMock()

        await self.org.cleanup_resources()

        self.org.remove_resource.assert_has_calls([
            mock.call(non_durable1),
            mock.call(non_durable2)
        ])
