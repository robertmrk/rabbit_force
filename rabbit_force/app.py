"""Application class definition"""
import asyncio
import logging

import uvloop

from .factories import create_message_sink, create_message_source, \
    create_router
from .exceptions import MessageSinkError


LOGGER = logging.getLogger(__name__)


class Application:  # pylint: disable=too-few-public-methods
    """Rabbit force application"""

    def __init__(self, config):
        """
        The application configures itself the first time :meth:`run` is called.
        If you want to run the application with a different configuration then
        a new Application instance should be created.

        :param dict config: Application configuration
        """
        #: The application's configuration
        self.config = config
        #: Marks whether the application is already configured or not
        self._configured = False
        #: A message source object
        self._source = None
        #: A message sink object
        self._sink = None
        #: A message router object
        self._router = None
        #: The set of currently running message forwarding tasks
        self._forwarding_tasks = set()
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
        self._source = await create_message_source(
            **self.config["source"]
        )
        self._sink = await create_message_sink(**self.config["sink"])
        self._router = create_router(**self.config["router"])
        self._configured = True

    async def _listen_for_messages(self):
        """Listen for incoming messages and route them to the appropriate
        brokers

        This method will block until it's cancelled. On cancellation it'll
        drain all the pending messages and forwarding tasks.
        """
        # open the message source
        await self._source.open()

        # consume messages until the message source is not closed, or until
        # all the messages are consumed from a closed message source
        while not self._source.closed or self._source.has_pending_messages:
            try:
                # await an incoming message
                source_name, message = await self._source.get_message()

                # forward the message in non blocking fashion (without awaiting
                # the tasks result)
                await self._schedule_message_forwarding(source_name, message)

            # on cancellation close the message source but continue to
            # consume pending messages until there is no more left
            except asyncio.CancelledError:
                await self._source.close()

        # if the source is closed and there are no more messages to consume,
        # await the completion of scheduled forwaring tasks
        await self._wait_scheduled_forwarding_tasks()

        # when all the messages are forwarded close the message sink
        await self._sink.close()

    async def _schedule_message_forwarding(self, source_name, message):
        """Create a task for forwarding the *message* from *source_name* and
        add it to the list of active forwarding tasks

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
        # add the task to the set of running tasks
        self._forwarding_tasks.add(forwarding_task)

    async def _wait_scheduled_forwarding_tasks(self):
        """Wait for all the active forwarding tasks to complete"""

        # check if there are any running forwarding tasks, and await them
        if self._forwarding_tasks:
            await asyncio.wait(self._forwarding_tasks, loop=self._loop)

    async def _forward_message(self, source_name, message):
        """Forward the *message* from *source_name* with the appropriate route

        :param str source_name: Name of the message source
        :param dict message: A message
        :return: A three element tuple which contains the forwarded message, \
        name of the message source and the routing parameters
        :rtype: tuple[dict, str, Route]
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
        return message, source_name, route

    def _forward_message_done(self, future):
        """Consume the result of a completed message forwarding task

        :param asyncio.Future future: A future object
        """
        self._forwarding_tasks.remove(future)

        try:
            message, source_name, route = future.result()
            channel = message["channel"]
            replay_id = message["data"]["event"]["replayId"]

            if route:
                LOGGER.info("Message %r on channel %r "
                            "from %r forwarded to %r.",
                            replay_id, channel, source_name, route)
            else:
                LOGGER.warning("No route found for message "
                               "%r on channel %r from %r, message dropped.",
                               replay_id, channel, source_name)
        except MessageSinkError as error:
            LOGGER.error("Failed to forward message. %s", str(error))
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed to forward message.")
