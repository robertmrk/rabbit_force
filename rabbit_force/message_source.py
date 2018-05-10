"""Message source class definitions"""
import asyncio
from abc import ABC, abstractmethod

from aiosfstream import Client
from aiosfstream.exceptions import AiosfstreamException, ClientInvalidOperation

from .exceptions import StreamingError, InvalidOperation


class MessageSource(ABC):
    """Abstract message source base class

    A message source's responsibility is to supply the application with
    incoming messages
    """
    @property
    @abstractmethod
    def closed(self):
        """Marks whether the message source is open or closed"""

    @property
    @abstractmethod
    def pending_count(self):
        """The number of pending incoming messages"""

    @property
    @abstractmethod
    def has_pending_messages(self):
        """Marks whether the client has any pending incoming messages"""

    @abstractmethod
    async def open(self):
        """Open the message source and start fetching messages"""

    @abstractmethod
    async def close(self):
        """Close the message source

        No more messages are fetched after calling this method, but there might
        still be some pending messages waiting to be consumed
        """

    @abstractmethod
    async def get_message(self):
        """Wait for an incoming message

        :return: Return the name of the message source and the incoming message
        :rtype: tuple[str, dict]
        :raise InvalidOperation: If the message source is closed and there \
        are no more pending incoming messages
        """


class SalesforceOrgMessageSource(MessageSource):
    """Message source for fetching Streaming API messages"""
    def __init__(self, name, salesforce_org):
        """
        :param str name: The name of the message source
        :param SalesforceOrg salesforce_org: A salesforce org object
        """
        self.name = name
        self.salesforce_org = salesforce_org
        self.client = Client(self.salesforce_org.authenticator,
                             connection_timeout=0)

    @property
    def closed(self):
        return self.client.closed

    @property
    def pending_count(self):
        return self.client.pending_count

    @property
    def has_pending_messages(self):
        return self.client.has_pending_messages

    async def open(self):
        # open the streaming client
        await self.client.open()
        # subscribe to all streaming resources of the org
        for resource in self.salesforce_org.resources.values():
            await self.client.subscribe(resource.channel_name)

    async def close(self):
        # close the streaming client
        await self.client.close()
        # remove non durable resources
        await self.salesforce_org.cleanup_resources()
        # close the org
        await self.salesforce_org.close()

    async def get_message(self):
        try:
            # wait for an incoming message
            message = await self.client.receive()
            # return the name of the message source and the received message
            return self.name, message

        # if there are no more messages to consume raise an error
        except ClientInvalidOperation as error:
            raise InvalidOperation(str(error)) from error

        # raise a StreamingError for all other aiosfstream errors
        except AiosfstreamException as error:
            raise StreamingError("Message reception failure.") from error


class MultiMessageSource(MessageSource):
    """Message source to gather and fetch messages from multiple message
    sources"""
    def __init__(self, sources):
        """
        :param list[MessageSource] sources: A list of message sources
        """
        self.sources = list(sources)
        self._closed = True

    @property
    def closed(self):
        return self._closed

    @property
    def pending_count(self):
        # return the sum of pending messages from all message sources
        return sum(source.pending_count for source in self.sources)

    @property
    def has_pending_messages(self):
        return self.pending_count > 0

    async def open(self):
        # open all message sources
        for source in self.sources:
            await source.open()
        self._closed = False

    async def close(self):
        # close all message sources
        for source in self.sources:
            await source.close()
        self._closed = True

    async def get_message(self):
        # create tasks for waiting on incoming messages from all sources
        tasks = [asyncio.ensure_future(_.get_message()) for _ in self.sources
                 if not _.closed or _.has_pending_messages]

        try:
            # wait until the first task completes
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.CancelledError:
            # if canceled, then cancel all the waiting tasks
            for task in tasks:
                task.cancel()
            raise

        # cancel all pending tasks
        for task in pending:
            task.cancel()

        # return the result from the first completed task
        return next(iter(done)).result()
