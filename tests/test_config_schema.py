from unittest import TestCase

from marshmallow import ValidationError, fields

from rabbit_force.config_schema import PushTopicSchema, \
    StreamingResourceSchema, StrictSchema, StreamingChannelSchema


class TestStrictSchema(TestCase):
    def setUp(self):
        class TestSchema(StrictSchema):
            foo = fields.String(required=True)

        self.schema_cls = TestSchema

    def test_rejects_unkown_fields(self):
        data = {
            "foo": "value",
            "bar": "value"
        }

        with self.assertRaisesRegex(ValidationError,
                                    r"{'bar': \['Unknown field'\]}"):
            self.schema_cls().load(data)


class TestPushTopicSchema(TestCase):
    def setUp(self):
        self.invalid_operation_for_erlier_error = \
            "'NotifyForOperationCreate', " \
            "'NotifyForOperationDelete', " \
            "'NotifyForOperationUndelete' and " \
            "'NotifyForOperationUpdate' can only be " \
            "specified for API version 29.0 and " \
            "later."

    def test_check_api_version_invalid_version(self):
        data = {
            "Name": "name",
            "ApiVersion": 12,
            "Query": "query string",
            "NotifyForOperations": "All"
        }

        with self.assertRaisesRegex(ValidationError, "'ApiVersion'"):
            PushTopicSchema().load(data)

    def test_check_api_version(self):
        data = {
            "Name": "name",
            "ApiVersion": 22,
            "Query": "query string",
            "NotifyForOperations": "All"
        }

        PushTopicSchema().load(data)

    def test_check_api_version_invalid_notify_for_operations(self):
        data = {
            "Name": "name",
            "ApiVersion": 29,
            "Query": "query string",
            "NotifyForOperations": "All"
        }

        with self.assertRaisesRegex(ValidationError,
                                    "'NotifyForOperations' can only be "
                                    "specified for API version 28.0 and "
                                    "earlier."):
            PushTopicSchema().load(data)

    def test_check_api_version_invalid_notify_for_create(self):
        data = {
            "Name": "name",
            "ApiVersion": 28,
            "Query": "query string",
            "NotifyForOperationCreate": True
        }

        with self.assertRaisesRegex(ValidationError,
                                    self.invalid_operation_for_erlier_error):
            PushTopicSchema().load(data)

    def test_check_api_version_invalid_notify_for_delete(self):
        data = {
            "Name": "name",
            "ApiVersion": 28,
            "Query": "query string",
            "NotifyForOperationDelete": True
        }

        with self.assertRaisesRegex(ValidationError,
                                    self.invalid_operation_for_erlier_error):
            PushTopicSchema().load(data)

    def test_check_api_version_invalid_notify_for_undelete(self):
        data = {
            "Name": "name",
            "ApiVersion": 28,
            "Query": "query string",
            "NotifyForOperationUndelete": True
        }

        with self.assertRaisesRegex(ValidationError,
                                    self.invalid_operation_for_erlier_error):
            PushTopicSchema().load(data)

    def test_check_api_version_invalid_notify_for_update(self):
        data = {
            "Name": "name",
            "ApiVersion": 28,
            "Query": "query string",
            "NotifyForOperationUpdate": True
        }

        with self.assertRaisesRegex(ValidationError,
                                    self.invalid_operation_for_erlier_error):
            PushTopicSchema().load(data)

    def test_check_required_fields_no_fields(self):
        data = {}

        with self.assertRaisesRegex(ValidationError,
                                    "'Either a single fields should be "
                                    "specified which uniquely identifies the "
                                    "resource or multiple fields which can be "
                                    "used to construct the resource.'"):
            PushTopicSchema().load(data)

    def test_check_required_fields_single_non_id_field(self):
        data = {"Query": "query string"}

        with self.assertRaisesRegex(ValidationError,
                                    "If only a single field is specified "
                                    "it should be a unique identifier like "
                                    "'Id' or 'Name'."):
            PushTopicSchema().load(data)

    def test_check_required_fields_single_id_field(self):
        data = {"Id": "id"}

        result = PushTopicSchema().load(data)

        self.assertEqual(result, data)

    def test_check_required_fields_single_name_field(self):
        data = {"Name": "name"}

        result = PushTopicSchema().load(data)

        self.assertEqual(result, data)

    def test_check_required_fields_multiple_definition_fields(self):
        data = {
            "Name": "name",
            "ApiVersion": 28,
            "Query": "query string"
        }

        result = PushTopicSchema().load(data)

        self.assertEqual(result, data)

    def test_check_required_fields_multiple_definition_fields_missing(self):
        data = {
            "Name": "name",
            "Query": "query string"
        }

        with self.assertRaisesRegex(ValidationError,
                                    "If multiple fields are specified it "
                                    "it should be a full resource "
                                    "definition where at least 'Name', "
                                    "'ApiVersion' and 'Query' are required."):
            PushTopicSchema().load(data)


class TestStreamingChannelSchema(TestCase):
    def test_check_required_fields_no_fields(self):
        data = {}

        with self.assertRaisesRegex(ValidationError,
                                    "'Either a single fields should be "
                                    "specified which uniquely identifies the "
                                    "resource or multiple fields which can be "
                                    "used to construct the resource.'"):
            StreamingChannelSchema().load(data)

    def test_check_required_fields_single_non_id_field(self):
        data = {"Description": "desc"}

        with self.assertRaisesRegex(ValidationError,
                                    "If only a single field is specified "
                                    "it should be a unique identifier like "
                                    "'Id' or 'Name'."):
            StreamingChannelSchema().load(data)

    def test_check_required_fields_single_id_field(self):
        data = {"Id": "id"}

        result = StreamingChannelSchema().load(data)

        self.assertEqual(result, data)

    def test_check_required_fields_single_name_field(self):
        data = {"Name": "name"}

        result = StreamingChannelSchema().load(data)

        self.assertEqual(result, data)

    def test_check_required_fields_multiple_definition_fields(self):
        data = {
            "Name": "name",
            "Description": "desc"
        }

        result = StreamingChannelSchema().load(data)

        self.assertEqual(result, data)


class TestStreamingResourceSchema(TestCase):
    def test_load_push_topic(self):
        data = {
            "type": "PushTopic",
            "spec": {
                "Name": "name",
                "ApiVersion": 22.0,
                "Query": "query string",
                "NotifyForOperations": "All"
            }
        }

        result = StreamingResourceSchema().load(data)

        expected_data = {
            "resource_type": data["type"],
            "resource_spec": data["spec"]
        }
        self.assertEqual(result, expected_data)

    def test_load_streaming_channel(self):
        data = {
            "type": "StreamingChannel",
            "spec": {
                "Name": "name",
                "Description": "desc"
            }
        }

        result = StreamingResourceSchema().load(data)

        expected_data = {
            "resource_type": data["type"],
            "resource_spec": data["spec"]
        }
        self.assertEqual(result, expected_data)
