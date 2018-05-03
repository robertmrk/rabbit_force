from unittest import TestCase, mock

import requests.exceptions
import simple_salesforce.exceptions

from rabbit_force.streaming_resources import StreamingResource, \
    PushTopicResource, StreamingChannelResource, StreamingResourceFactory, \
    StreamingResourceType
from rabbit_force.exceptions import NetworkError, SalesforceError, \
    RabbitForceValueError


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
        self.resource_client = mock.MagicMock()
        setattr(self.rest_client, self.type_name, self.resource_client)
        self.factory = StreamingResourceFactory(self.type_name,
                                                self.rest_client)

    def test_get_resource(self):
        type_cls = mock.MagicMock()
        StreamingResource.RESOURCE_TYPES[self.type_name] = type_cls
        spec = {"Name": "resource_name"}
        self.factory._get_resource = mock.MagicMock(return_value=spec)

        result = self.factory.get_resource(spec)

        self.assertEqual(result, type_cls.return_value)
        self.factory._get_resource.assert_called_with(spec)
        type_cls.assert_called_with(spec)
        del StreamingResource.RESOURCE_TYPES[self.type_name]

    def test_get_resource_network_error(self):
        error_message = "message"
        error = requests.exceptions.RequestException(error_message)
        self.factory._get_resource = mock.MagicMock(side_effect=error)

        with self.assertRaisesRegex(NetworkError, error_message):
            self.factory.get_resource({})

    def test_get_resource_salesforce_error(self):
        error_message = "message"
        error = simple_salesforce.exceptions.SalesforceError("url", 400,
                                                             "resource",
                                                             error_message)
        self.factory._get_resource = mock.MagicMock(side_effect=error)

        with self.assertRaisesRegex(SalesforceError, str(error)):
            self.factory.get_resource({})

    def test__get_resource_with_single_value_pair(self):
        self.factory._get_resource_by_identifier = mock.MagicMock()
        self.factory._create_resource = mock.MagicMock()
        spec = {"Id": "id"}

        result = self.factory._get_resource(spec)

        self.assertEqual(result,
                         self.factory._get_resource_by_identifier.return_value)
        self.factory._get_resource_by_identifier.assert_called_with("Id", "id")
        self.factory._create_resource.assert_not_called()

    def test__get_resource_with_multiple_value_pairs(self):
        self.factory._get_resource_by_identifier = mock.MagicMock()
        self.factory._create_resource = mock.MagicMock()
        spec = {"Name": "name", "Id": "id"}

        result = self.factory._get_resource(spec)

        self.assertEqual(result, self.factory._create_resource.return_value)
        self.factory._create_resource.assert_called_with(spec)
        self.factory._get_resource_by_identifier.assert_not_called()

    def test_get_resource_by_identifier_for_id(self):
        self.factory._get_resource_by_id = mock.MagicMock()
        self.factory._get_resource_by_name = mock.MagicMock()

        result = self.factory._get_resource_by_identifier("Id", "id")

        self.assertEqual(result, self.factory._get_resource_by_id.return_value)
        self.factory._get_resource_by_id.assert_called_with("id")
        self.factory._get_resource_by_name.assert_not_called()

    def test_get_resource_by_identifier_for_name(self):
        self.factory._get_resource_by_id = mock.MagicMock()
        self.factory._get_resource_by_name = mock.MagicMock()

        result = self.factory._get_resource_by_identifier("Name", "name")

        self.assertEqual(result,
                         self.factory._get_resource_by_name.return_value)
        self.factory._get_resource_by_name.assert_called_with("name")
        self.factory._get_resource_by_id.assert_not_called()

    def test_get_resource_by_identifier_error(self):
        self.factory._get_resource_by_id = mock.MagicMock()
        self.factory._get_resource_by_name = mock.MagicMock()
        identifier_name = "unknown"

        with self.assertRaisesRegex(RabbitForceValueError,
                                    f"'{identifier_name}' is not a unique "
                                    f"streaming resource identifier."):
            self.factory._get_resource_by_identifier(identifier_name, "value")

        self.factory._get_resource_by_name.assert_not_called()
        self.factory._get_resource_by_id.assert_not_called()

    def test_get_resource_by_id(self):
        resource_id = "id"

        result = self.factory._get_resource_by_id(resource_id)

        self.assertEqual(result, self.resource_client.get.return_value)
        self.resource_client.get.assert_called_with(resource_id)

    def test_get_resource_id_by_name(self):
        id_value = "id_value"
        response = {
            "records": [{"Id": id_value}]
        }
        self.rest_client.query.return_value = response
        name = "name"

        result = self.factory._get_resource_id_by_name(name)

        self.assertEqual(result, id_value)
        self.rest_client.query.assert_called_with(
            f"SELECT Id FROM {self.type_name} WHERE Name='{name}'")

    def test_get_resource_id_by_name_no_results(self):
        response = {
            "records": []
        }
        self.rest_client.query.return_value = response
        name = "name"
        with self.assertRaisesRegex(SalesforceError,
                                    f"There is no {self.type_name} with "
                                    f"the name '{name}'."):
            self.factory._get_resource_id_by_name(name)

        self.rest_client.query.assert_called_with(
            f"SELECT Id FROM {self.type_name} WHERE Name='{name}'")

    def test_create_resource_with_existing_resource(self):
        spec = {"Name": "resource_name"}
        resource_id = "id"
        resource = {}
        self.factory._get_resource_id_by_name = mock.MagicMock(
            return_value=resource_id
        )
        self.factory._get_resource_by_id = mock.MagicMock(
            return_value=resource
        )

        result = self.factory._create_resource(spec)

        self.assertEqual(result, resource)
        self.factory._get_resource_id_by_name.assert_called_with(spec["Name"])
        self.resource_client.update.assert_called_with(resource_id, spec)
        self.factory._get_resource_by_id.assert_called_with(resource_id)

    def test_create_resource_with_non_existing_resource(self):
        spec = {"Name": "resource_name"}
        resource_id = "id"
        resource = {}
        self.factory._get_resource_id_by_name = mock.MagicMock(
            side_effect=SalesforceError()
        )
        self.factory._get_resource_by_id = mock.MagicMock(
            return_value=resource
        )
        self.resource_client.create.return_value = {"id": resource_id}

        result = self.factory._create_resource(spec)

        self.assertEqual(result, resource)
        self.factory._get_resource_id_by_name.assert_called_with(spec["Name"])
        self.resource_client.create.assert_called_with(spec)
        self.factory._get_resource_by_id.assert_called_with(resource_id)

    def test_get_resource_by_name(self):
        resource_id = "id"
        self.factory._get_resource_id_by_name = mock.MagicMock(
            return_value=resource_id
        )
        self.factory._get_resource_by_id = mock.MagicMock()
        name = "name"

        result = self.factory._get_resource_by_name(name)

        self.assertEqual(result, self.factory._get_resource_by_id.return_value)
        self.factory._get_resource_id_by_name.assert_called_with(name)
        self.factory._get_resource_by_id.assert_called_with(resource_id)
