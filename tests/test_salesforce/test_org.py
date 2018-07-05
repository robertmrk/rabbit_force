from asynctest import TestCase, mock

from rabbit_force.salesforce import SalesforceOrg, SalesforceRestClient, \
    StreamingResourceFactory


class TestSalesforceOrg(TestCase):
    @mock.patch(SalesforceOrg.__module__ + ".PasswordAuthenticator")
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
            self.password,
            loop=self.loop
        )

    def test_init(self):
        self.assertEqual(self.org.authenticator, self.authenticator)
        self.auth_cls.assert_called_with(
            self.consumer_key,
            self.consumer_secret,
            self.username,
            self.password
        )
        self.assertIs(self.org.authenticator, self.auth_cls.return_value)
        self.assertEqual(self.org.resources, {})
        self.assertIsInstance(self.org._rest_client, SalesforceRestClient)
        self.assertEqual(self.org._rest_client._loop, self.loop)
        self.assertIsInstance(self.org._resource_factory,
                              StreamingResourceFactory)

    async def test_add_resource(self):
        resource_type = object()
        resource_spec = object()
        self.org._resource_factory = mock.MagicMock()
        self.org._resource_factory.create_resource = mock.CoroutineMock()
        durable = True
        self.org._get_client = mock.CoroutineMock()

        result = await self.org.add_resource(resource_type, resource_spec,
                                             durable)

        self.assertEqual(
            result,
            self.org._resource_factory.create_resource.return_value
        )
        self.org._resource_factory.create_resource.assert_called_with(
            resource_type,
            resource_spec
        )
        self.assertEqual(result.durable, durable)
        self.assertEqual(self.org.resources[result.name], result)

    async def test_remove_resource(self):
        resource = mock.MagicMock()
        resource.type_name = "name"
        self.org._rest_client = mock.MagicMock()
        self.org._rest_client.delete = mock.CoroutineMock()

        await self.org.remove_resource(resource)

        self.org._rest_client.delete.assert_called_with(resource.type_name,
                                                        resource.id)

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

    async def test_close(self):
        self.org._rest_client = mock.MagicMock()
        self.org._rest_client.close = mock.CoroutineMock()

        await self.org.close()

        self.org._rest_client.close.assert_called()
