"""Application class definition"""
import asyncio
import logging
import signal
from collections import namedtuple

import uvloop

from .factories import create_message_sink, create_message_source, \
    create_router
from .exceptions import MessageSinkError


LOGGER = logging.getLogger(__name__)
SourceMessagePair = namedtuple("SourceMessagePair", ["source_name", "message"])

# pylint: disable=too-few-public-methods, too-many-instance-attributes


class Application:
    """Rabbit force application"""

    def __init__(self, config, ignore_replay_storage_errors=False,
                 ignore_sink_errors=False,
                 source_connection_timeout=10.0):
        """
        The application configures itself the first time :meth:`run` is called.
        If you want to run the application with a different configuration then
        a new Application instance should be created.

        :param dict config: Application configuration
        :param bool ignore_replay_storage_errors: If True then no exceptions \
        will be raised in case of a network error occurs in the replay marker \
        storage object
        :param bool ignore_sink_errors: If True then no exceptions \
        will be raised in case a message sink error occurs
        :param source_connection_timeout: The maximum amount of time to wait \
        for the message source to re-establish a connection with the server \
        when the connection fails.
        :type source_connection_timeout: int, float or None
        """
        #: The application's configuration
        self.config = config
        #: Marks whether to raise exceptions on replay storage errors or not
        self.ignore_replay_storage_errors = ignore_replay_storage_errors
        #: Marks whether to raise exceptions on message sink errors or not
        self.ignore_sink_errors = ignore_sink_errors
        #: Maximum allowed connection timeout for message source
        self.source_connection_timeout = source_connection_timeout
        #: Marks whether the application is already configured or not
        self._configured = False
        #: A message source object
        self._source = None
        #: A message sink object
        self._sink = None
        #: A message router object
        self._router = None
        #: The currently running message forwarding tasks
        self._forwarding_tasks = {}
        #: Event loop
        self._loop = None

    def run(self):
        """Run the Rabbit force application, listen for and forward messages
        until a keyboard interrupt occurs"""

        # use the uvloop event loop policy
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # create an event loop and create the main task
        self._loop = asyncio.get_event_loop()
        task = asyncio.ensure_future(self._run(), loop=self._loop)

        # cancel the main task on SIGINT or SIGTERM
        for signal_id in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(signal_id, task.cancel)

        # run the task until completion
        try:
            self._loop.run_until_complete(task)

        # on a keyboard interrupt cancel the main task and await its completion
        except KeyboardInterrupt:
            task.cancel()
            self._loop.run_until_complete(task)

    async def _run(self):
        """Configure the application and listen for incoming messages until
        cancellation"""

        # configure the application
        await self._configure()

        # listen for incoming messages
        await self._listen_for_messages()

    async def _configure(self):
        """Create and configure collaborator objects"""
        LOGGER.info("Configuring application ...")

        self._source = await create_message_source(
            **self.config["source"],
            ignore_replay_storage_errors=self.ignore_replay_storage_errors,
            connection_timeout=self.source_connection_timeout,
            loop=self._loop
        )
        self._sink = await create_message_sink(
            **self.config["sink"],
            loop=self._loop
        )
        self._router = create_router(**self.config["router"])
        self._configured = True

    async def _listen_for_messages(self):
        """Listen for incoming messages and route them to the appropriate
        brokers

        This method will block until it's cancelled. On cancellation it'll
        drain all the pending messages and forwarding tasks.
        """
        try:
            # open the message source
            await self._source.open()

            # consume messages until the message source is not closed, or until
            # all the messages are consumed from a closed message source
            while not self._source.closed or self._source.has_pending_messages:
                try:
                    # await an incoming message
                    source_name, message = await self._source.get_message()

                    # forward the message in non blocking fashion
                    # (without awaiting the tasks result)
                    await self._schedule_message_forwarding(source_name,
                                                            message)

                # on cancellation close the message source but continue to
                # consume pending messages until there is no more left
                except asyncio.CancelledError:
                    await self._source.close()
                    LOGGER.info("Shutting down ...")

        finally:
            # close the source in case it wasn't closed in the inner loop
            # (idempotent if already closed)
            await self._source.close()

            # if the source is closed and there are no more messages to
            # consume, await the completion of scheduled forwaring tasks
            await self._wait_scheduled_forwarding_tasks()

            # when all the messages are forwarded close the message sink
            await self._sink.close()

    async def _schedule_message_forwarding(self, source_name, message):
        """Create a task for forwarding the *message* from *source_name* and
        add it to the map of active forwarding tasks

        :param str source_name: Name of the message source
        :param dict message: A message
        """
        # create a task to forward the message
        forwarding_task = asyncio.ensure_future(
            self._forward_message(source_name, message),
            loop=self._loop
        )
        # set a callback to consume the tasks result
        forwarding_task.add_done_callback(self._forward_message_done)
        # add the task and message to the map of running tasks
        self._forwarding_tasks[forwarding_task] = \
            SourceMessagePair(source_name, message)

    async def _wait_scheduled_forwarding_tasks(self):
        """Wait for all the active forwarding tasks to complete"""

        # check if there are any running forwarding tasks, and await them
        if self._forwarding_tasks:
            await asyncio.wait(self._forwarding_tasks, loop=self._loop)

    async def _forward_message(self, source_name, message):
        """Forward the *message* from *source_name* with the appropriate route

        :param str source_name: Name of the message source
        :param dict message: A message
        :return: The routing parameters used to forward the message or None \
        if no suitable route was found
        :rtype: Route or None
        """
        # find a matching route for the message
        route = self._router.find_route(source_name, message)

        # if a route was found for the message then forward it using the
        # routing parameters
        if route is not None:
            await self._sink.consume_message(message,
                                             route.broker_name,
                                             route.exchange_name,
                                             route.routing_key,
                                             route.properties)

        # return the message, source_name and the routing parameters
        return route

    def _forward_message_done(self, future):
        """Consume the result of a completed message forwarding task

        :param asyncio.Future future: A future object
        """
        # remove task from the map of running tasks
        source_message_pair = self._forwarding_tasks.pop(future)
        # extract message and source information
        source_name = source_message_pair.source_name
        channel = source_message_pair.message["channel"]
        replay_id = source_message_pair.message["data"]["event"]["replayId"]

        try:
            route = future.result()

            if route:
                LOGGER.info("Forwarded message %r on channel %r "
                            "from %r to %r.",
                            replay_id, channel, source_name, route)
            else:
                LOGGER.warning("Dropped message %r on channel %r from %r, "
                               "no route found.",
                               replay_id, channel, source_name)
        except MessageSinkError as error:
            if self.ignore_sink_errors:
                LOGGER.error("Dropped message %r on channel %r from %r. %s",
                             replay_id, channel, source_name, str(error))
            else:
                raise

# pylint: enable=too-few-public-methods, too-many-instance-attributes
