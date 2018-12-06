from unittest import TestCase, mock
import json

from marshmallow import ValidationError, fields
import yaml

from rabbit_force.config import PushTopicSchema, \
    StreamingResourceSchema, StrictSchema, StreamingChannelSchema, \
    get_config_loader, load_config
from rabbit_force.exceptions import ConfigurationError


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
                                    r"{'bar': \['Unknown field.'\]}"):
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


class TestGetConfigLoader(TestCase):
    def test_for_json(self):
        file_path = "file.json"

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = get_config_loader(file_path)

        self.assertIs(result, json.load)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:Using JSON config loader for "
            f"{file_path!r}"
        ])

    def test_for_yaml(self):
        file_path = "file.yaml"

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = get_config_loader(file_path)

        self.assertIs(result, yaml.safe_load)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:Using YAML config loader for "
            f"{file_path!r}"
        ])

    def test_for_yml(self):
        file_path = "file.yml"

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = get_config_loader(file_path)

        self.assertIs(result, yaml.safe_load)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:Using YAML config loader for "
            f"{file_path!r}"
        ])

    def test_for_invalid_extension(self):
        file_path = "file.xml"

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = get_config_loader(file_path)

        self.assertIsNone(result)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:No config loader found for "
            f"{file_path!r}"
        ])

    def test_for_without_extension(self):
        file_path = "file"

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = get_config_loader(file_path)

        self.assertIsNone(result)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:No config loader found for "
            f"{file_path!r}"
        ])

    def test_for_empty_file_path(self):
        file_path = ""

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = get_config_loader(file_path)

        self.assertIsNone(result)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:No config loader found for "
            f"{file_path!r}"
        ])


class TestLoadConfig(TestCase):
    @mock.patch("rabbit_force.config.get_config_loader")
    def test_no_loader(self, get_config_loader):
        get_config_loader.return_value = None
        file_path = "file"

        with self.assertRaisesRegex(ConfigurationError,
                                    f"Unrecognized configuration file "
                                    f"format for {file_path!r}."):
            load_config(file_path)

        get_config_loader.assert_called_with(file_path)

    @mock.patch("rabbit_force.config.open")
    @mock.patch("rabbit_force.config.get_config_loader")
    def test_error_on_load(self, get_config_loader, open_func):
        loader = mock.MagicMock()
        error = Exception("message")
        loader.side_effect = error
        get_config_loader.return_value = loader
        file_path = "file"
        file_obj = object()
        open_cm = mock.MagicMock()
        open_cm.__enter__.return_value = file_obj
        open_func.return_value = open_cm

        with self.assertRaisesRegex(ConfigurationError,
                                    f"Failed to load configuration "
                                    f"file {file_path!r}. {error!s}"),\
                self.assertLogs("rabbit_force.config", "DEBUG") as log:
            load_config(file_path)

        get_config_loader.assert_called_with(file_path)
        loader.assert_called_with(file_obj)
        open_cm.__exit__.assert_called()
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:Loading configuration from "
            f"{file_path!r}"
        ])

    @mock.patch("rabbit_force.config.ApplicationConfigSchema")
    @mock.patch("rabbit_force.config.open")
    @mock.patch("rabbit_force.config.get_config_loader")
    def test_error_on_validation(self, get_config_loader, open_func,
                                 schema_cls):
        loader = mock.MagicMock()
        get_config_loader.return_value = loader
        file_path = "file"
        file_obj = object()
        open_cm = mock.MagicMock()
        open_cm.__enter__.return_value = file_obj
        open_func.return_value = open_cm
        schema = mock.MagicMock()
        error = ValidationError("message")
        schema.load.side_effect = error
        schema_cls.return_value = schema

        with self.assertRaisesRegex(ConfigurationError,
                                    f"Failed to validate configuration "
                                    f"file {file_path!r}. {error!s}"),\
                self.assertLogs("rabbit_force.config", "DEBUG") as log:
            load_config(file_path)

        get_config_loader.assert_called_with(file_path)
        loader.assert_called_with(file_obj)
        open_cm.__exit__.assert_called()
        schema.load.assert_called_with(loader.return_value)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:Loading configuration from "
            f"{file_path!r}",
            "DEBUG:rabbit_force.config:Validating configuration"
        ])

    @mock.patch("rabbit_force.config.ApplicationConfigSchema")
    @mock.patch("rabbit_force.config.open")
    @mock.patch("rabbit_force.config.get_config_loader")
    def test_success(self, get_config_loader, open_func, schema_cls):
        loader = mock.MagicMock()
        get_config_loader.return_value = loader
        file_path = "file"
        file_obj = object()
        open_cm = mock.MagicMock()
        open_cm.__enter__.return_value = file_obj
        open_func.return_value = open_cm
        schema = mock.MagicMock()
        validated_config = object()
        schema.load.return_value = validated_config
        schema_cls.return_value = schema

        with self.assertLogs("rabbit_force.config", "DEBUG") as log:
            result = load_config(file_path)

        self.assertEqual(result, validated_config)
        get_config_loader.assert_called_with(file_path)
        loader.assert_called_with(file_obj)
        open_cm.__exit__.assert_called()
        schema.load.assert_called_with(loader.return_value)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.config:Loading configuration from "
            f"{file_path!r}",
            "DEBUG:rabbit_force.config:Validating configuration"
        ])
