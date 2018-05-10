"""Streaming resource types"""
from abc import ABC, abstractmethod
from enum import Enum, unique

from .exceptions import SalesforceNotFoundError, SpecificationError


@unique
class StreamingResourceType(str, Enum):
    """Streaming resource type names supported by Salesforce"""
    #: PushTopic resource name
    PUSH_TOPIC = "PushTopic"
    #: StreamingChannel resource name
    STREAMING_CHANNEL = "StreamingChannel"


class StreamingResource(ABC):
    """Base class for streaming resource types"""
    #: Dictionary of resource types by name
    RESOURCE_TYPES = {}

    def __init__(self, resource_definition, durable=True):
        """
        :param dict resource_definition: The resources server side \
        representation
        :param bool durable: Whether the resource should be deleted or should \
        it be left on the server
        """
        #: The resource's server side representation
        self.definition = resource_definition
        #: Marks whether the resource should be deleted or should
        #: it be left on the server
        self.durable = durable

    @property
    def id(self):  # pylint: disable=invalid-name
        """Resource id"""
        return self.definition["Id"]

    @property
    def name(self):
        """Resource name"""
        return self.definition["Name"]

    @property
    def description(self):
        """Resource description"""
        return self.definition["Description"]

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


class StreamingResourceFactory:  # pylint: disable=too-few-public-methods
    """Factory class for creating StreamingResource objects from resource
    specifications"""
    def __init__(self, rest_client):
        """
        :param rest_client: Salesforce REST API client
        :type rest_client: SalesforceApi
        """
        #: Salesforce REST API client
        self.client = rest_client

    async def create_resource(self, type_name, resource_spec):
        """Create a StreamingResource object of type *type_name* based on the
        given *resource_spec*

        If the *resource_spec* contains a single unique identifier like \
        ``Name`` or ``Id`, then the existing resource will be loaded and \
        returned. If the *resource_spec* contains multiple key-value pairs,
        then it's assumed to be a resource definition, and based on it a new \
        resource will be created or an existing one will be updated if \
        a resource already exists with the given ``Name`` attribute.

        :param str type_name: Name of a streaming resource type
        :param dict resource_spec: A resource specification, which either \
        contains all attributes required for creating the resource, or \
        contains a single unique identifier of an existing resource, such as \
        ``Name`` or ``Id``
        :return: A streaming resource object
        :rtype: StreamingResource
        :raise NetworkError: If a network connection error occurs
        :raise SalesforceRestError: If there is no existing resource for the \
        given single identifier in *resource_spec* or if Salesforce fails to \
        create a new resource from the *resource_spec*
        """
        if type_name not in StreamingResource.RESOURCE_TYPES:
            raise SpecificationError(f"There is not streaming resource type "
                                     f"with the name '{type_name}'.")

        resource_definition = await self._get_resource(type_name,
                                                       resource_spec)
        resource_cls = StreamingResource.RESOURCE_TYPES[type_name]
        return resource_cls(resource_definition)

    async def _get_resource(self, type_name, resource_spec):
        """Create a streaming resource of type *type_name* based on the
        given *resource_spec*

        If the *resource_spec* contains a single unique identifier like \
        ``Name`` or ``Id`, then the existing resource will be loaded and \
        returned. If the *resource_spec* contains multiple key-value pairs,
        then it's assumed to be a resource definition, and based on it a new \
        resource will be created or an existing one will be updated if \
        a resource already exists with the given ``Name`` attribute.

        :param str type_name: Name of a streaming resource type
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
            return await self._get_resource_by_identifier(type_name,
                                                          name, value)
        # otherwise it must be a full resource definition
        return await self._create_resource(type_name, resource_spec)

    async def _get_resource_by_identifier(self, type_name, identifier_name,
                                          identifier_value):
        """Get the attributes of an existing streaming resource of type
        *type_name* based on the given *identifier_name* and *identifier_value*

        :param str type_name: Name of a streaming resource type
        :param str identifier_name: A unique resource identifier like \
        ``Name`` or ``Id``
        :param str identifier_value: The value of the identifier
        :return: Streaming resource attributes
        :rtype: dict
        :raise SpecificationError: If the identifier_name is not ``Name`` \
        or ``Id``
        """
        if identifier_name == "Name":
            return await self._get_resource_by_name(type_name,
                                                    identifier_value)
        elif identifier_name == "Id":
            return await self._get_resource_by_id(type_name, identifier_value)
        else:
            raise SpecificationError(f"'{identifier_name}' is not a unique "
                                     f"streaming resource identifier.")

    async def _get_resource_by_id(self, type_name, resource_id):
        """Get the attributes of an existing streaming resource of type
        *type_name* with the given *resource_id*

        :param str type_name: Name of a streaming resource type
        :param str resource_id: The id of a streaming resource
        :return: Streaming resource attributes
        :rtype: dict
        """
        return await self.client.get(type_name, resource_id)

    async def _get_resource_by_name(self, type_name, name):
        """Get the attributes of an existing streaming resource of type
        *type_name* with the given *name*

        :param str type_name: Name of a streaming resource type
        :param str name: The name of a streaming resource
        :return: Streaming resource attributes
        :rtype: dict
        """
        resource_id = await self._get_resource_id_by_name(type_name, name)
        return await self._get_resource_by_id(type_name, resource_id)

    async def _get_resource_id_by_name(self, type_name, name):
        """Find the id value of the resource of type *type_name* with the
        given *name*

        :param str type_name: Name of a streaming resource type
        :param str name: The name of a streaming resource
        :return: The id of a streaming resource
        :rtype: str
        """
        # get the id for the given name
        response = await self.client.query(f"SELECT Id FROM {type_name} "
                                           f"WHERE Name='{name}'")
        # if there are not records with the given name raise an error
        if not response["records"]:
            raise SalesforceNotFoundError(f"There is no {type_name} with "
                                          f"the name '{name}'.")
        # return the id
        return response["records"][0]["Id"]

    async def _create_resource(self, type_name, resource_definition):
        """Create a streaming resource of type *type_name* based on the
        given *resource_definition*

        Based on the *resource_definition* a new resource will be created \
        or an existing one will be updated if a resource already exists with \
         the given ``Name`` attribute.

        :param str type_name: Name of a streaming resource type
        :param dict resource_definition: A resource definition, which \
        contains all attributes required for creating the resource
        :return: Streaming resource attributes
        :rtype: dict
        """
        name = resource_definition["Name"]
        # try to find the resource with the given name, and if it exists then
        # update it
        try:
            resource_id = await self._get_resource_id_by_name(type_name, name)
            await self.client.update(type_name, resource_id,
                                     resource_definition)
            response = await self._get_resource_by_id(type_name, resource_id)

        # if there is no resource with the given name then create it
        except SalesforceNotFoundError:
            create_response = await self.client.create(type_name,
                                                       resource_definition)
            response = await self._get_resource_by_id(type_name,
                                                      create_response["id"])
        return response
