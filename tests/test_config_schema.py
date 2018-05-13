from unittest import TestCase

from marshmallow import ValidationError, fields

from rabbit_force.config_schema import PushTopicSchema, \
    StreamingResourceSchema, StrictSchema, resource_class_selector, \
    StreamingChannelSchema


class TestStrictSchema(TestCase):
    def setUp(self):
        class TestSchema(StrictSchema):
            foo = fields.String(required=True)

        self.schema_cls = TestSchema

    def test_init(self):
        schema = self.schema_cls()

        self.assertTrue(schema.strict)

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

        result = StreamingResourceSchema().load(data).data

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

        result = StreamingResourceSchema().load(data).data

        expected_data = {
            "resource_type": data["type"],
            "resource_spec": data["spec"]
        }
        self.assertEqual(result, expected_data)


class TestResourceClassSelector(TestCase):
    def test_selects_push_topic(self):
        result = resource_class_selector({}, {"type": "PushTopic"})

        self.assertIsInstance(result, PushTopicSchema)

    def test_selects_streaming_channel(self):
        result = resource_class_selector({}, {"type": "StreamingChannel"})

        self.assertIsInstance(result, StreamingChannelSchema)
