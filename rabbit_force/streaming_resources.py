"""Streaming resource types"""
from abc import ABC, abstractmethod


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


# pylint: disable=useless-super-delegation

class PushTopicResource(StreamingResource, type_name="PushTopic"):
    """Represents a query that is the basis for notifying listeners of \
    changes to records in an organization"""
    def __init__(self, name, *, resource_attributes):
        """
        :param str name: Descriptive name of the PushTopic, such as \
        MyNewCases or TeamUpdatedContacts. Limit: 25 characters. This value \
        identifies the channel and must be unique.
        :param resource_attributes: All resource attributes
        """
        super().__init__(name, resource_attributes=resource_attributes)

    @property
    def channel_name(self):
        return "/topic/" + self.name


class StreamingChannelResource(StreamingResource,
                               type_name="StreamingChannel"):
    """Represents a channel that is the basis for notifying listeners of \
    generic Streaming API events"""
    def __init__(self, name, *, resource_attributes):
        """
        :param str name: Descriptive name of the StreamingChannel. Limit: 80 \
        characters, alphanumeric and “_”, “/” characters only. Must start \
        with “/u/”. This value identifies the channel and must be unique.
        :param resource_attributes: All resource attributes
        """
        super().__init__(name, resource_attributes=resource_attributes)

    @property
    def channel_name(self):
        return self.name

# pylint: enable=too-few-public-methods,useless-super-delegation
