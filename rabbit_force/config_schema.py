"""Configuration schemas"""
from marshmallow import Schema, fields, validates_schema, ValidationError
from marshmallow.validate import Length, Range, OneOf
from marshmallow_polyfield import PolyField

from .source.salesforce import StreamingResourceType


class StrictSchema(Schema):
    """Common schema base class with strict validation

    Raises exceptions on validation errors instead of failing silently and
    rejects unknown fields
    """
    def __init__(self):
        # raise exceptions for validation errors
        super().__init__(strict=True)

    # pylint: disable=unused-argument
    @validates_schema(pass_original=True)
    def check_unknown_fields(self, data, original_data):
        """Check for the presence and reject unknown fields

        :raise marshmallow.ValidationError: If an unknown field is found
        """
        # get the difference of the loaded and specified fields
        unknown_fields = set(original_data) - set(self.fields)
        # raise an error if any surplus fields are present
        if unknown_fields:
            raise ValidationError('Unknown field', list(unknown_fields))

    # pylint: enable=unused-argument


class PushTopicSchema(StrictSchema):
    """Configuration schema for PushTopic resources"""

    # PushTopic fields are validated according to
    # https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/\
    # api_streaming/pushtopic.htm
    Name = fields.String(required=True, validate=Length(min=1, max=25))
    ApiVersion = fields.Float(required=True,
                              validate=Range(min=20.0, max=42.0))
    IsActive = fields.Boolean(default=True)
    NotifyForFields = fields.String(validate=OneOf(["All",
                                                    "Referenced",
                                                    "Select",
                                                    "Where"]))
    Description = fields.String(default=None, validate=Length(max=400))
    NotifyForOperationCreate = fields.Boolean(default=True)
    NotifyForOperationUpdate = fields.Boolean(default=True)
    NotifyForOperationDelete = fields.Boolean(default=True)
    NotifyForOperationUndelete = fields.Boolean(default=True)
    NotifyForOperations = fields.String(validate=OneOf(["All",
                                                        "Create",
                                                        "Extended",
                                                        "Update"]))
    Query = fields.String(required=True, validate=Length(min=1, max=1300))

    @validates_schema
    def check_api_version(self, data):  # pylint: disable=no-self-use
        """Check for invalid fields for the specified API version

        :raise marshmallow.ValidationError: If any invalid fields found for \
        the specified API version
        """
        # skip validation if the ApiVersion field is not present, which might
        # happen even when it's specified but it's value fails on validation
        if "ApiVersion" not in data:
            return

        # check for the presence of old fields for a newer API version
        if (data["ApiVersion"] >= 29.0 and
                "NotifyForOperations" in data):
            raise ValidationError("'NotifyForOperations' can only be specified"
                                  " for API version 28.0 and earlier.")

        # check for the presence of new fields for an older API version
        elif (data["ApiVersion"] <= 28.0 and
              ("NotifyForOperationCreate" in data or
               "NotifyForOperationDelete" in data or
               "NotifyForOperationUndelete" in data or
               "NotifyForOperationUpdate" in data)):
            raise ValidationError("'NotifyForOperationCreate', "
                                  "'NotifyForOperationDelete', "
                                  "'NotifyForOperationUndelete' and "
                                  "'NotifyForOperationUpdate' can only be "
                                  "specified for API version 29.0 and later.")


class StreamingChannelSchema(StrictSchema):
    """Configuration schema for StreamingChannel resources"""

    # StreamingChannel fields are validated according to
    # https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/\
    # api_streaming/streamingChannel.htm
    Name = fields.String(required=True, validate=Length(min=1, max=80))
    Description = fields.String(default=None, validate=Length(max=255))

# pylint: disable=unused-argument


def resource_class_selector(data, parent_data):
    """Return the appropriate type of schema object for the given resource
    data

    :param dict data: The configuration values for the resource
    :param dict parent_data: The complete configuration for the resource \
    which contains the resource's type
    :return: A resource schema object
    :rtype: StrictSchema
    """
    schema_map = {
        StreamingResourceType.PUSH_TOPIC: PushTopicSchema,
        StreamingResourceType.STREAMING_CHANNEL: StreamingChannelSchema
    }
    type_name = parent_data["type"]
    return schema_map[type_name]()

# pylint: enable=unused-argument


class StreamingResourceSchema(StrictSchema):
    """Configuration schema for streaming resources"""

    type = fields.String(required=True, attribute="type_name",
                         validate=OneOf([_.value for _ in
                                         StreamingResourceType]))
    spec = PolyField(deserialization_schema_selector=resource_class_selector,
                     serialization_schema_selector=resource_class_selector,
                     required=True, attribute="resource_spec")
