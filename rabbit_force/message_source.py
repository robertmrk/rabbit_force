"""Message source class definitions"""
import asyncio
from abc import ABC, abstractmethod
import pickle
import logging
import reprlib

from aiosfstream import Client, ReplayMarkerStorage, ReplayOption
from aiosfstream.exceptions import AiosfstreamException, ClientInvalidOperation
import aioredis

from .exceptions import MessageSourceError, InvalidOperation, \
    ReplayStorageError


LOGGER = logging.getLogger(__name__)


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
    # pylint: disable=too-many-arguments

    """Message source for fetching Streaming API messages"""
    def __init__(self, name, salesforce_org, replay=ReplayOption.NEW_EVENTS,
                 replay_fallback=None, connection_timeout=10.0, loop=None):
        """
        :param str name: The name of the message source
        :param SalesforceOrg salesforce_org: A salesforce org object
        :param replay: A ReplayOption or an object capable of storing replay \
        ids if you want to take advantage of Salesforce's replay extension. \
        You can use one of the :obj:`ReplayOptions <ReplayOption>`, or \
        an object that supports the MutableMapping protocol like :obj:`dict`, \
        :obj:`~collections.defaultdict`, :obj:`~shelve.Shelf` etc. or a \
        custom :obj:`ReplayMarkerStorage` implementation.
        :type replay: aiosfstream.ReplayOption, \
        aiosfstream.ReplayMarkerStorage, collections.abc.MutableMapping or None
        :param replay_fallback: Replay fallback policy, for when a subscribe \
        operation fails because a replay id was specified for a message \
        outside the retention window
        :type replay_fallback: aiosfstream.ReplayOption
        :param connection_timeout: The maximum amount of time to wait for the \
        client to re-establish a connection with the server when the \
        connection fails.
        :type connection_timeout: int, float or None
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        #: Event loop
        self._loop = loop or asyncio.get_event_loop()
        self.name = name
        self.salesforce_org = salesforce_org
        self.client = Client(self.salesforce_org.authenticator,
                             replay=replay,
                             replay_fallback=replay_fallback,
                             connection_timeout=connection_timeout,
                             loop=self._loop)

    # pylint: enable=too-many-arguments
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

        log_lines = [f"\t* from {_.type_name.value!s} {_.name!r} "
                     f"on channel {_.channel_name!r}"
                     for _ in self.salesforce_org.resources.values()]
        log_lines.append(f"With replay storage "
                         f"{self.client.replay_storage!r}.")
        LOGGER.info("Listening for messages from Salesforce org %r: \n%s",
                    self.name, "\n".join(log_lines))

    async def close(self):
        # don't close if already closed
        if not self.closed:
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

        # raise a MessageSourceError for all other aiosfstream errors
        except AiosfstreamException as error:
            raise MessageSourceError(f"Failed message reception from "
                                     f"Salesforce org {self.name!r}. "
                                     f"{error!s}") from error


class MultiMessageSource(MessageSource):
    """Message source to gather and fetch messages from multiple message
    sources"""
    def __init__(self, sources, loop=None):
        """
        :param list[MessageSource] sources: A list of message sources
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        #: Event loop
        self._loop = loop or asyncio.get_event_loop()
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
        tasks = [asyncio.ensure_future(_.get_message(),
                                       loop=self._loop) for _ in self.sources
                 if not _.closed or _.has_pending_messages]

        try:
            # wait until the first task completes
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
                loop=self._loop
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


class RedisReplayStorage(ReplayMarkerStorage):
    """Redis ReplayMarkerStorage implementation"""
    def __init__(self, address, *, key_prefix=None,
                 ignore_network_errors=False, loop=None, **kwargs):
        """
        :param str address: Server address
        :param str key_prefix: A prefix string to add to all keys
        :param bool ignore_network_errors: If True then no exceptions will \
        be raised in case of a network error.
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        :param dict kwargs: Additional key-value parameters for Redis
        """
        super().__init__()
        #: Event loop
        self._loop = loop or asyncio.get_event_loop()
        self.key_prefix = key_prefix or ""
        self.address = address
        self.additional_params = kwargs
        self.ignore_network_errors = ignore_network_errors
        self._redis = None

    def __repr__(self):
        cls_name = type(self).__name__
        fmt_spec = "{}(address={}, key_prefix={}, additional_params={}, " \
                   "ignore_network_errors={})"
        return fmt_spec.format(cls_name,
                               reprlib.repr(self.address),
                               reprlib.repr(self.key_prefix),
                               reprlib.repr(self.additional_params),
                               reprlib.repr(self.ignore_network_errors))

    def _get_key(self, subscription):
        """Create a key value for the given *subscription*

        :param str subscription: The name of the subscription
        :return: The key value that should be used when writing to the datebase
        :rtype: str
        """
        return self.key_prefix + ":" + subscription

    async def _get_redis(self):
        """Get a Redis client

        :return: Redis client
        :rtype: aioredis.Redis
        """
        # if not yet initialised then create the redis pool with the address
        # and the additional redis parameters passed in init
        if not self._redis:
            self._redis = await aioredis.create_redis_pool(
                self.address, loop=self._loop, **self.additional_params
            )
        # return the existing client object
        return self._redis

    async def get_replay_marker(self, subscription):
        # get a key for the subscription
        key = self._get_key(subscription)

        try:
            # get the client object
            redis = await self._get_redis()

            # retrieve the value of the key
            result = await redis.get(key)

        # on connection error log the error and return None
        except ConnectionError as error:
            error_message = (f"Failed to get the replay marker from redis for "
                             f"subscription {subscription!r} with {self!s}. "
                             f"{error!s}")

            # if network errors should be ignored only log the error
            if self.ignore_network_errors:
                LOGGER.error(error_message)
                return None
            # otherwise raise an exception
            else:
                raise ReplayStorageError(error_message) from error

        # if there is a value stored for the key, then return the deserialized
        # value
        if result is not None:
            return pickle.loads(result)

        # otherwise return None
        return None

    async def set_replay_marker(self, subscription, replay_marker):
        # get a key for the subscription
        key = self._get_key(subscription)

        try:
            # get the client object
            redis = await self._get_redis()

            # serialize the replay marker
            value = pickle.dumps(replay_marker)

            # set the value for the key
            await redis.set(key, value)

        # on connection error log the error
        except ConnectionError as error:
            error_message = (f"Failed to set the replay marker in redis for "
                             f"subscription {subscription!r} with {self!s}. "
                             f"{error!s}")

            # if network errors should be ignored only log the error
            if self.ignore_network_errors:
                LOGGER.error(error_message)
            # otherwise raise an exception
            else:
                raise ReplayStorageError(error_message) from error
