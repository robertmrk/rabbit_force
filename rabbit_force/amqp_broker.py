"""AmqpBroker class definition"""
import reprlib
import asyncio

import aioamqp

from .exceptions import NetworkError


class AmqpBroker:  # pylint: disable=too-many-instance-attributes
    """Represents an AMQP message broker capable of publishing messages"""
    def __init__(self, host, *, port=None, login='guest',
                 password='guest', virtualhost='/', ssl=False,
                 login_method='AMQPLAIN', insist=False, verify_ssl=True,
                 loop=None):
        """
        :param str host: the host to connect to
        :param list[dict] exchange_specs: List of exchange specifications \
        that can be passed to \
        :py:meth:`aioamqp.channel.Channel.exchange_declare`
        :param port: broker port
        :type port: int or None
        :param str login: login
        :param str password: password
        :param str virtualhost: AMQP virtualhost to use for this connection
        :param bool ssl: Create an SSL connection instead of a plain \
        unencrypted one
        :param str login_method: AMQP auth method
        :param bool insist: Insist on connecting to a server
        :param bool verify_ssl: Verify server's SSL certificate \
        (True by default)
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.virtualhost = virtualhost
        self.ssl = ssl
        self.login_method = login_method
        self.insist = insist
        self.verify_ssl = verify_ssl
        self._loop = loop or asyncio.get_event_loop()
        self._transport = None
        self._protocol = None
        self._channel = None

    def __repr__(self):
        cls_name = type(self).__name__
        fmt_spec = "{}(host={}, port={}, login={}, password={}, " \
                   "virtualhost={}, ssl={}, login_method={}, insist={}, " \
                   "verify_ssl={})"
        return fmt_spec.format(cls_name,
                               reprlib.repr(self.host),
                               reprlib.repr(self.port),
                               reprlib.repr(self.login),
                               reprlib.repr(self.password),
                               reprlib.repr(self.virtualhost),
                               reprlib.repr(self.ssl),
                               reprlib.repr(self.login_method),
                               reprlib.repr(self.insist),
                               reprlib.repr(self.verify_ssl))

    async def _get_channel(self):
        """Creates a new AMQP channel or returns an existing one if it's open

        :return: An AMQP channel object
        :rtype: aioamqp.channel.Channel
        :raise ConnectionError: If a network connection error occurs
        """
        # if there is no channel object yet or if it's closed
        if self._channel is None or not self._channel.is_open:
            # create new transport and protocol objects by connectin to the
            # broker
            self._transport, self._protocol = await aioamqp.connect(
                self.host,
                port=self.port,
                login=self.login,
                password=self.password,
                virtualhost=self.virtualhost,
                ssl=self.ssl,
                login_method=self.login_method,
                insist=self.insist,
                verify_ssl=self.verify_ssl,
                loop=self._loop
            )
            # create a new channel object
            self._channel = await self._protocol.channel()

        # return the existing channel object
        return self._channel

    # pylint: disable=too-many-arguments

    async def exchange_declare(self, exchange_name, type_name, passive=False,
                               durable=False, auto_delete=False, no_wait=False,
                               arguments=None):
        """Declare an AMQP exchange

        :param str exchange_name: Name of the exchange
        :param str type_name: The exchange type (fanout, direct, topics …)
        :param bool passive: Ff set, the server will reply with Declare-Ok if \
        the exchange already exists with the same name, and raise an error \
        if not. Checks for the same parameter as well.
        :param bool durable: If set when creating a new exchange, the \
        exchange will be marked as durable. Durable exchanges remain active \
        when a server restarts.
        :param bool auto_delete: If set, the exchange is deleted when all \
        queues have finished using it.
        :param bool no_wait: If set, the server will not respond to the method
        :param dict arguments: AMQP arguments to be passed when creating the \
        exchange
        :raise NetworkError: If a network related error occurs
        """
        try:
            # get an open AMQP channel
            channel = await self._get_channel()

            # declare the exchange
            await channel.exchange_declare(exchange_name, type_name, passive,
                                           durable, auto_delete, no_wait,
                                           arguments)
        except ConnectionError as error:
            raise NetworkError(f"Network error during declaring exchange with "
                               f"{self!r}. {error!s}") from error

    # pylint: enable=too-many-arguments

    async def publish(self, payload, exchange_name, routing_key,
                      properties=None):
        """Publish the message's *payload* on exchange *exchange_name* with \
        the given *routing_key* and pass the *properties* of the message

        :param bytes payload: The message's serialized payload
        :param str exchange_name: The name of the exchange to publish the \
        message on
        :param str routing_key: The message's routing key
        :param dict properties: Message properties
        :raise NetworkError: If a network related error occurs
        """
        try:
            # get an open AMQP channel
            channel = await self._get_channel()

            # publish the message
            await channel.publish(payload, exchange_name, routing_key,
                                  properties)
        except ConnectionError as error:
            raise NetworkError(f"Network error during publishing message with "
                               f"{self!r}. {error!s}") from error

    async def close(self):
        """Close the broker object"""
        # don't close the transport and protocol if the protocol is already
        # closed
        if not self._protocol.connection_closed.is_set():
            await self._protocol.close()
            self._transport.close()
