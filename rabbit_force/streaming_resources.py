"""Streaming resource types"""
from abc import ABC, abstractmethod
from enum import Enum, unique

import requests.exceptions
import simple_salesforce.exceptions

from .exceptions import NetworkError, SalesforceError, RabbitForceValueError


@unique
class StreamingResourceType(str, Enum):
    PUSH_TOPIC = "PushTopic"
    STREAMING_CHANNEL = "StreamingChannel"


# pylint: disable=too-few-public-methods

class StreamingResource(ABC):
    """Base class for streaming resource types"""
    #: Dictionary of resource types by name
    RESOURCE_TYPES = {}

    def __init__(self, name, *, resource_attributes):
        """
        :param str name: Descriptive name of the StreamingResource. \
        This value identifies the channel and must be unique
        :param resource_attributes: All resource attributes
        """
        self.name = name
        self.resource_attributes = resource_attributes

    @property
    @abstractmethod
    def channel_name(self):
        """Name of the streaming channel"""

    def __init_subclass__(cls, type_name, **kwargs):
        """Register subclass *cls* for the given *type_name*"""
        super().__init_subclass__(**kwargs)
        cls.type_name = type_name
        cls.RESOURCE_TYPES[type_name] = cls
        return cls


class PushTopicResource(
        StreamingResource, type_name=StreamingResourceType.PUSH_TOPIC):
    """Represents a query that is the basis for notifying listeners of \
    changes to records in an organization"""

    @property
    def channel_name(self):
        return "/topic/" + self.name


class StreamingChannelResource(
        StreamingResource, type_name=StreamingResourceType.STREAMING_CHANNEL):
    """Represents a channel that is the basis for notifying listeners of \
    generic Streaming API events"""

    @property
    def channel_name(self):
        return self.name

# pylint: enable=too-few-public-methods


class StreamingResourceFactory:  # pylint: disable=too-few-public-methods
    """Factory class for creating StreamingResource objects"""
    def __init__(self, type_name, rest_client):
        """
        :param str type_name: Name of a streaming resource type
        :param rest_client: Salesforce REST API client
        :type rest_client: simple_salesforce.Salesforce
        """
        #: Salesforce REST API client
        self.rest_client = rest_client
        #: Name of a streaming resource type
        self.type_name = type_name
        #: Salesforce REST API client for handling a single type of resource
        self.resource_client = getattr(self.rest_client, type_name)

    def get_resource(self, resource_spec):
        """Create a StreamingResource object based on the given *resource_spec*

        If the *resource_spec* contains a single unique identifier like \
        ``Name`` or ``Id`, then the existing resource will be loaded and \
        returned. If the *resource_spec* contains multiple key-value pairs,
        then it's assumed to be a resource definition, and based on it a new \
        resource will be created or an existing one will be updated if \
        a resource already exists with the given ``Name`` attribute.

        :param dict resource_spec: A resource specification, which either \
        contains all attributes required for creating the resource, or \
        contains a single unique identifier of an existing resource, such as \
        ``Name`` or ``Id``
        :return: A streaming resource object
        :rtype: StreamingResource
        :raise NetworkError: If a network connection error occurs
        :raise SalesforceError: If there is no existing resource for the \
        given single identifier in *resource_spec* or if Salesforce fails to \
        create a new resource from the *resource_spec*
        """
        try:
            attributes = self._get_resource(resource_spec)
            resource_cls = StreamingResource.RESOURCE_TYPES[self.type_name]
            return resource_cls(attributes["Name"],
                                resource_attributes=attributes)
        except simple_salesforce.exceptions.SalesforceError as error:
            raise SalesforceError(str(error)) from error
        except requests.exceptions.RequestException as error:
            raise NetworkError(str(error)) from error

    def _get_resource(self, resource_spec):
        """Create a streaming resource based on the given *resource_spec*

        If the *resource_spec* contains a single unique identifier like \
        ``Name`` or ``Id`, then the existing resource will be loaded and \
        returned. If the *resource_spec* contains multiple key-value pairs,
        then it's assumed to be a resource definition, and based on it a new \
        resource will be created or an existing one will be updated if \
        a resource already exists with the given ``Name`` attribute.

        :param dict resource_spec: A resource specification, which either \
        contains all attributes required for creating the resource, or \
        contains a single unique identifier of an existing resource, such as \
        ``Name`` or ``Id``
        :return: Streaming resource attributes
        :rtype: dict
        """
        # if the *resource_spec* contains a single item it must be an
        # identifier
        if len(resource_spec) == 1:
            name, value = list(resource_spec.items())[0]
            return self._get_resource_by_identifier(name, value)
        # otherwise it must be a full resource definition
        return self._create_resource(resource_spec)

    def _get_resource_by_identifier(self, identifier_name, identifier_value):
        """Get the attributes of an existing streaming resource based on the \
        given *identifier_name* and *identifier_value*

        :param str identifier_name: A unique resource identifier like \
        ``Name`` or ``Id``
        :param str identifier_value: The value of the identifier
        :return: Streaming resource attributes
        :rtype: dict
        :raise RabbitForceValueError: If the identifier_name is not ``Name`` \
        or ``Id``
        """
        if identifier_name == "Name":
            return self._get_resource_by_name(identifier_value)
        elif identifier_name == "Id":
            return self._get_resource_by_id(identifier_value)
        else:
            raise RabbitForceValueError(f"'{identifier_name}' is not a unique "
                                        f"streaming resource identifier.")

    def _get_resource_by_id(self, resource_id):
        """Get the attributes of an existing streaming resource with the \
        given *resource_id*

        :param str resource_id: The id of a streaming resource
        :return: Streaming resource attributes
        :rtype: dict
        """
        return self.resource_client.get(resource_id)

    def _get_resource_by_name(self, name):
        """Get the attributes of an existing streaming resource with the \
        given *name*

        :param str name: The name of a streaming resource
        :return: Streaming resource attributes
        :rtype: dict
        """
        resource_id = self._get_resource_id_by_name(name)
        return self._get_resource_by_id(resource_id)

    def _get_resource_id_by_name(self, name):
        """Find the id value of the resource with the given *name*

        :param str name: The name of a streaming resource
        :return: The id of a streaming resource
        :rtype: str
        """
        # get the id for the given name
        response = self.rest_client.query(f"SELECT Id FROM {self.type_name} "
                                          f"WHERE Name='{name}'")
        # if there are not records with the given name raise an error
        if not response["records"]:
            raise SalesforceError(f"There is no {self.type_name} with "
                                  f"the name '{name}'.")
        # return the id
        return response["records"][0]["Id"]

    def _create_resource(self, resource_definition):
        """Create a streaming resource based on the given *resource_definition*

        Based on the *resource_definition* a new resource will be created \
        or an existing one will be updated if a resource already exists with \
         the given ``Name`` attribute.

        :param dict resource_definition: A resource definition, which \
        contains all attributes required for creating the resource
        :return: Streaming resource attributes
        :rtype: dict
        """
        name = resource_definition["Name"]
        # try to find the resource with the given name, and if it exists then
        # update it
        try:
            resource_id = self._get_resource_id_by_name(name)
            self.resource_client.update(resource_id, resource_definition)
            response = self._get_resource_by_id(resource_id)

        # if there is no resource with the given name then create it
        except SalesforceError:
            create_response = self.resource_client.create(resource_definition)
            response = self._get_resource_by_id(create_response["id"])
        return response
