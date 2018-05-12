from asynctest import TestCase, mock

from rabbit_force.source.salesforce import StreamingResource, \
    PushTopicResource, StreamingChannelResource, StreamingResourceFactory, \
    StreamingResourceType
from rabbit_force.exceptions import SalesforceNotFoundError, \
    SpecificationError


class TestStreamingResource(TestCase):
    def setUp(self):
        self. type_name = "ResourceName"

        class Resource(StreamingResource, type_name=self.type_name):
            @property
            def channel_name(self):
                return "name"

        self.resource_cls = Resource
        self.resource = Resource({
            "Id": "id",
            "Name": "name",
            "Description": "desc"
        })

    def test_registers_subclass(self):
        self.assertEqual(StreamingResource.RESOURCE_TYPES[self.type_name],
                         self.resource_cls)

    def test_returns_name(self):
        self.assertEqual(self.resource.name, self.resource.definition["Name"])

    def test_returns_id(self):
        self.assertEqual(self.resource.id, self.resource.definition["Id"])

    def test_returns_description(self):
        self.assertEqual(self.resource.description,
                         self.resource.definition["Description"])


class TestPushTopicResource(TestCase):
    def test_registers_in_superclass(self):
        self.assertEqual(
            StreamingResource.RESOURCE_TYPES[StreamingResourceType.PUSH_TOPIC],
            PushTopicResource
        )

    def test_returns_channel_name(self):
        definition = {"Name": "name"}
        topic = PushTopicResource(definition)

        self.assertEqual(topic.channel_name, "/topic/" + definition["Name"])


class TestStreamingChannelResource(TestCase):
    def test_registers_in_superclass(self):
        self.assertEqual(
            StreamingResource.RESOURCE_TYPES[
                StreamingResourceType.STREAMING_CHANNEL],
            StreamingChannelResource
        )

    def test_returns_channel_name(self):
        definition = {"Name": "name"}
        topic = StreamingChannelResource(definition)

        self.assertEqual(topic.channel_name, definition["Name"])


class TestStreamingResourceFactory(TestCase):
    def setUp(self):
        self.type_name = "resource_type"
        self.rest_client = mock.MagicMock()
        self.factory = StreamingResourceFactory(self.rest_client)

    async def test_create_resource(self):
        type_cls = mock.MagicMock()
        StreamingResource.RESOURCE_TYPES[self.type_name] = type_cls
        spec = {"Name": "resource_name"}
        self.factory._get_resource = mock.CoroutineMock(return_value=spec)

        result = await self.factory.create_resource(self.type_name, spec)

        self.assertEqual(result, type_cls.return_value)
        self.factory._get_resource.assert_called_with(self.type_name, spec)
        type_cls.assert_called_with(spec)
        del StreamingResource.RESOURCE_TYPES[self.type_name]

    async def test_create_resource_invalid_type_name(self):
        spec = {"Name": "resource_name"}
        self.factory._get_resource = mock.CoroutineMock(return_value=spec)

        with self.assertRaisesRegex(SpecificationError,
                                    f"There is not streaming resource type "
                                    f"with the name '{self.type_name}'."):
            await self.factory.create_resource(self.type_name, spec)

        self.factory._get_resource.assert_not_called()

    async def test__get_resource_with_single_value_pair(self):
        self.factory._get_resource_by_identifier = mock.CoroutineMock()
        self.factory._create_resource = mock.CoroutineMock()
        spec = {"Id": "id"}

        result = await self.factory._get_resource(self.type_name, spec)

        self.assertEqual(result,
                         self.factory._get_resource_by_identifier.return_value)
        self.factory._get_resource_by_identifier.assert_called_with(
            self.type_name, "Id", "id")
        self.factory._create_resource.assert_not_called()

    async def test__get_resource_with_multiple_value_pairs(self):
        self.factory._get_resource_by_identifier = mock.CoroutineMock()
        self.factory._create_resource = mock.CoroutineMock()
        spec = {"Name": "name", "Id": "id"}

        result = await self.factory._get_resource(self.type_name, spec)

        self.assertEqual(result, self.factory._create_resource.return_value)
        self.factory._create_resource.assert_called_with(self.type_name, spec)
        self.factory._get_resource_by_identifier.assert_not_called()

    async def test_get_resource_by_identifier_for_id(self):
        self.factory._get_resource_by_id = mock.CoroutineMock()
        self.factory._get_resource_by_name = mock.CoroutineMock()

        result = await self.factory._get_resource_by_identifier(self.type_name,
                                                                "Id", "id")

        self.assertEqual(result, self.factory._get_resource_by_id.return_value)
        self.factory._get_resource_by_id.assert_called_with(self.type_name,
                                                            "id")
        self.factory._get_resource_by_name.assert_not_called()

    async def test_get_resource_by_identifier_for_name(self):
        self.factory._get_resource_by_id = mock.CoroutineMock()
        self.factory._get_resource_by_name = mock.CoroutineMock()

        result = await self.factory._get_resource_by_identifier(self.type_name,
                                                                "Name", "name")

        self.assertEqual(result,
                         self.factory._get_resource_by_name.return_value)
        self.factory._get_resource_by_name.assert_called_with(self.type_name,
                                                              "name")
        self.factory._get_resource_by_id.assert_not_called()

    async def test_get_resource_by_identifier_error(self):
        self.factory._get_resource_by_id = mock.CoroutineMock()
        self.factory._get_resource_by_name = mock.CoroutineMock()
        identifier_name = "unknown"

        with self.assertRaisesRegex(SpecificationError,
                                    f"'{identifier_name}' is not a unique "
                                    f"streaming resource identifier."):
            await self.factory._get_resource_by_identifier(self.type_name,
                                                           identifier_name,
                                                           "value")

        self.factory._get_resource_by_name.assert_not_called()
        self.factory._get_resource_by_id.assert_not_called()

    async def test_get_resource_by_id(self):
        resource_id = "id"
        self.rest_client.get = mock.CoroutineMock()

        result = await self.factory._get_resource_by_id(self.type_name,
                                                        resource_id)

        self.assertEqual(result, self.rest_client.get.return_value)
        self.rest_client.get.assert_called_with(self.type_name, resource_id)

    async def test_get_resource_id_by_name(self):
        id_value = "id_value"
        response = {
            "records": [{"Id": id_value}]
        }
        self.rest_client.query = mock.CoroutineMock(return_value=response)
        name = "name"

        result = await self.factory._get_resource_id_by_name(self.type_name,
                                                             name)

        self.assertEqual(result, id_value)
        self.rest_client.query.assert_called_with(
            f"SELECT Id FROM {self.type_name} WHERE Name='{name}'")

    async def test_get_resource_id_by_name_no_results(self):
        response = {
            "records": []
        }
        self.rest_client.query = mock.CoroutineMock(return_value=response)
        name = "name"
        with self.assertRaisesRegex(SalesforceNotFoundError,
                                    f"There is no {self.type_name} with "
                                    f"the name '{name}'."):
            await self.factory._get_resource_id_by_name(self.type_name, name)

        self.rest_client.query.assert_called_with(
            f"SELECT Id FROM {self.type_name} WHERE Name='{name}'")

    async def test_create_resource_with_existing_resource(self):
        spec = {"Name": "resource_name"}
        resource_id = "id"
        resource = {}
        self.factory._get_resource_id_by_name = mock.CoroutineMock(
            return_value=resource_id
        )
        self.factory._get_resource_by_id = mock.CoroutineMock(
            return_value=resource
        )
        self.rest_client.update = mock.CoroutineMock()

        result = await self.factory._create_resource(self.type_name, spec)

        self.assertEqual(result, resource)
        self.factory._get_resource_id_by_name.assert_called_with(
            self.type_name, spec["Name"])
        self.rest_client.update.assert_called_with(self.type_name,
                                                   resource_id, spec)
        self.factory._get_resource_by_id.assert_called_with(self.type_name,
                                                            resource_id)

    async def test_create_resource_with_non_existing_resource(self):
        spec = {"Name": "resource_name"}
        resource_id = "id"
        resource = {}
        self.factory._get_resource_id_by_name = mock.CoroutineMock(
            side_effect=SalesforceNotFoundError()
        )
        self.factory._get_resource_by_id = mock.CoroutineMock(
            return_value=resource
        )
        self.rest_client.create = mock.CoroutineMock(
            return_value={"id": resource_id}
        )

        result = await self.factory._create_resource(self.type_name, spec)

        self.assertEqual(result, resource)
        self.factory._get_resource_id_by_name.assert_called_with(
            self.type_name, spec["Name"])
        self.rest_client.create.assert_called_with(self.type_name, spec)
        self.factory._get_resource_by_id.assert_called_with(self.type_name,
                                                            resource_id)

    async def test_get_resource_by_name(self):
        resource_id = "id"
        self.factory._get_resource_id_by_name = mock.CoroutineMock(
            return_value=resource_id
        )
        self.factory._get_resource_by_id = mock.CoroutineMock()
        name = "name"

        result = await self.factory._get_resource_by_name(self.type_name, name)

        self.assertEqual(result, self.factory._get_resource_by_id.return_value)
        self.factory._get_resource_id_by_name.assert_called_with(
            self.type_name, name)
        self.factory._get_resource_by_id.assert_called_with(self.type_name,
                                                            resource_id)
