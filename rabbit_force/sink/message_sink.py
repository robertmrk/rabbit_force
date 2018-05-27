"""Message sink class definitions"""
import asyncio
from abc import ABC, abstractmethod
import json

from ..exceptions import MessageSinkError


class MessageSink(ABC):
    """Abstract message sink base class

    A message sink's responsibility is to consume outgoing messages
    """

    # pylint: disable=too-many-arguments
    @abstractmethod
    async def consume_message(self, message, sink_name, exchange_name,
                              routing_key, properties=None):
        """Forward the *message* with the sink specified with *sink_name*

        :param dict message: An outgoing message
        :param str sink_name: The name of the sink that should consume the \
        message
        :param str exchange_name: The name of the exchange which should \
        receive the message
        :param str routing_key: The message's routing key parameter
        :param dict properties: Additional message properties. Every \
        additional property will be forwarded by the sink except for \
        ``content_type`` and ``content_encoding`` which will be overwritten
        """

    # pylint: enable=too-many-arguments

    @abstractmethod
    async def close(self):
        """Close the message sink"""


class AmqpMessageSink(MessageSink):
    """Message sink for publishing the consumed messages with AMQP"""

    ENCODING = "utf-8"
    CONTENT_TYPE = "application/json"

    def __init__(self, transport, protocol, json_dumps=json.dumps):
        """
        :param asyncio.BaseTransport transport: A transport object
        :param aioamqp.AmqpProtocol protocol: AMQP protocol object
        :param json_dumps: Function for JSON serialization, the default is \
        :func:`json.dumps`
        :type json_dumps: :func:`callable`
        """
        self.transport = transport
        self.protocol = protocol
        self.channel = None
        self._json_dumps = json_dumps

    async def _get_channel(self):
        """Get an open channel object

        :return: A channel object
        :rtype: aioamqp.Channel
        """
        if self.channel is None:
            self.channel = await self.protocol.channel()
        return self.channel

    # pylint: disable=too-many-arguments
    async def consume_message(self, message, sink_name, exchange_name,
                              routing_key, properties=None):
        serialized_message = self._json_dumps(message).encode(self.ENCODING)

        if properties is None:
            properties = {}
        properties["content_type"] = self.CONTENT_TYPE
        properties["content_encoding"] = self.ENCODING

        channel = await self._get_channel()
        await channel.publish(serialized_message, exchange_name,
                              routing_key, properties=properties)

    # pylint: enable=too-many-arguments

    async def close(self):
        await self.protocol.close()
        self.transport.close()


class MultiMessageSink(MessageSink):
    """Message sink to route consumed messages between multiple message
    sinks"""
    def __init__(self, sinks, loop=None):
        """
        :param list[MessageSource] sources: A list of message sources
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        #: Event loop
        self._loop = loop or asyncio.get_event_loop()
        #: Message sink list
        self.sinks = sinks

    # pylint: disable=too-many-arguments

    async def consume_message(self, message, sink_name, exchange_name,
                              routing_key, properties=None):
        try:
            sink = self.sinks[sink_name]
        except KeyError as error:
            raise MessageSinkError(f"Sink named {sink_name!r} "
                                   f"doesn't exists") from error
        await sink.consume_message(message, sink_name, exchange_name,
                                   routing_key, properties)

    # pylint: enable=too-many-arguments

    async def close(self):
        for sink in self.sinks.values():
            await sink.close()
