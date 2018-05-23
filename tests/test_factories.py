from asynctest import TestCase, mock

from rabbit_force.factories import create_salesforce_org


class TestCreateSalesforceOrg(TestCase):
    @mock.patch("rabbit_force.factories.SalesforceOrg")
    async def test_create(self, org_cls):
        consumer_key = "key"
        consumer_secret = "secret"
        username = "username"
        password = "password"
        resource_spec = {"key": "value"}
        streaming_resource_specs = [resource_spec]
        org_mock = mock.MagicMock()
        org_mock.add_resource = mock.CoroutineMock()
        org_cls.return_value = org_mock

        result = await create_salesforce_org(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            username=username,
            password=password,
            streaming_resource_specs=streaming_resource_specs,
            loop=self.loop
        )

        self.assertIs(result, org_mock)
        org_cls.assert_called_with(
            consumer_key,
            consumer_secret,
            username,
            password,
            loop=self.loop
        )
        org_mock.add_resource.assert_called_with(**resource_spec)
