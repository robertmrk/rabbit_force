import reprlib

from asynctest import TestCase, mock

from rabbit_force.amqp_broker import AmqpBroker
from rabbit_force.exceptions import NetworkError


class TestAmqpBroker(TestCase):
    def setUp(self):
        self.host = "host"
        self.exchange_specs = [{"key": "value"}]
        self.port = 1234
        self.login = "login"
        self.password = "password"
        self.virtualhost = "virt_host"
        self.ssl = True
        self.login_method = "plain"
        self.insist = True
        self.verify_ssl = True
        self.broker = AmqpBroker(
            self.host,
            port=self.port,
            login=self.login,
            password=self.password,
            virtualhost=self.virtualhost,
            ssl=self.ssl,
            login_method=self.login_method,
            insist=self.insist,
            verify_ssl=self.verify_ssl,
            loop=self.loop
        )

    def test_init(self):
        self.assertIs(self.broker.host, self.host)
        self.assertIs(self.broker.port, self.port)
        self.assertIs(self.broker.login, self.login)
        self.assertIs(self.broker.password, self.password)
        self.assertIs(self.broker.virtualhost, self.virtualhost)
        self.assertIs(self.broker.ssl, self.ssl)
        self.assertIs(self.broker.login_method, self.login_method)
        self.assertIs(self.broker.insist, self.insist)
        self.assertIs(self.broker.verify_ssl, self.verify_ssl)
        self.assertIs(self.broker._loop, self.loop)
        self.assertIsNone(self.broker._transport)
        self.assertIsNone(self.broker._protocol)
        self.assertIsNone(self.broker._channel)

    def test_repr(self):
        result = repr(self.broker)

        cls_name = type(self.broker).__name__
        fmt_spec = "{}(host={}, port={}, login={}, password={}, " \
                   "virtualhost={}, ssl={}, login_method={}, insist={}, " \
                   "verify_ssl={})"
        expected_rexult = fmt_spec.format(cls_name,
                                          reprlib.repr(self.host),
                                          reprlib.repr(self.port),
                                          reprlib.repr(self.login),
                                          reprlib.repr(self.password),
                                          reprlib.repr(self.virtualhost),
                                          reprlib.repr(self.ssl),
                                          reprlib.repr(self.login_method),
                                          reprlib.repr(self.insist),
                                          reprlib.repr(self.verify_ssl))
        self.assertEqual(result, expected_rexult)

    @mock.patch("rabbit_force.amqp_broker.aioamqp")
    async def test_get_channel_creates_channel(self, aioamqp_mod):
        transport = object()
        protocol = mock.MagicMock()
        aioamqp_mod.connect = mock.CoroutineMock(return_value=(transport,
                                                               protocol))
        channel = object()
        protocol.channel = mock.CoroutineMock(return_value=channel)

        result = await self.broker._get_channel()

        self.assertIs(result, channel)
        self.assertIs(self.broker._transport, transport)
        self.assertIs(self.broker._protocol, protocol)
        self.assertIs(self.broker._channel, channel)
        aioamqp_mod.connect.assert_called_with(
            self.host,
            port=self.port,
            login=self.login,
            password=self.password,
            virtualhost=self.virtualhost,
            ssl=self.ssl,
            login_method=self.login_method,
            insist=self.insist,
            verify_ssl=self.verify_ssl,
            loop=self.loop
        )

    @mock.patch("rabbit_force.amqp_broker.aioamqp")
    async def test_get_channel_creates_channel_if_closed(self, aioamqp_mod):
        self.broker._channel = mock.MagicMock()
        self.broker._channel.is_open = False
        self.broker._transport = object()
        self.broker._protocol = object()
        transport = object()
        protocol = mock.MagicMock()
        aioamqp_mod.connect = mock.CoroutineMock(return_value=(transport,
                                                               protocol))
        channel = object()
        protocol.channel = mock.CoroutineMock(return_value=channel)

        result = await self.broker._get_channel()

        self.assertIs(result, channel)
        self.assertIs(self.broker._transport, transport)
        self.assertIs(self.broker._protocol, protocol)
        self.assertIs(self.broker._channel, channel)
        aioamqp_mod.connect.assert_called_with(
            self.host,
            port=self.port,
            login=self.login,
            password=self.password,
            virtualhost=self.virtualhost,
            ssl=self.ssl,
            login_method=self.login_method,
            insist=self.insist,
            verify_ssl=self.verify_ssl,
            loop=self.loop
        )

    @mock.patch("rabbit_force.amqp_broker.aioamqp")
    async def test_get_channel_returns_existing_channel(self, aioamqp_mod):
        channel = mock.MagicMock()
        channel.is_open = True
        self.broker._channel = channel

        result = await self.broker._get_channel()

        self.assertIs(result, channel)
        aioamqp_mod.connect.assert_not_called()

    async def test_exchnage_declare(self):
        exchange_name = "ex_name"
        type_name = "topic"
        passive = True
        durable = True
        auto_delete = True
        no_wait = True
        arguments = object()
        channel = mock.MagicMock()
        channel.exchange_declare = mock.CoroutineMock()
        self.broker._get_channel = mock.CoroutineMock(return_value=channel)

        await self.broker.exchange_declare(exchange_name, type_name, passive,
                                           durable, auto_delete, no_wait,
                                           arguments)

        channel.exchange_declare.assert_called_with(exchange_name, type_name,
                                                    passive, durable,
                                                    auto_delete, no_wait,
                                                    arguments)

    async def test_exchnage_declare_on_connection_error(self):
        exchange_name = "ex_name"
        type_name = "topic"
        passive = True
        durable = True
        auto_delete = True
        no_wait = True
        arguments = object()
        channel = mock.MagicMock()
        error = ConnectionError("message")
        channel.exchange_declare = mock.CoroutineMock(side_effect=error)
        self.broker._get_channel = mock.CoroutineMock(return_value=channel)

        with self.assertRaisesRegex(NetworkError, str(error)):
            await self.broker.exchange_declare(exchange_name, type_name,
                                               passive, durable, auto_delete,
                                               no_wait, arguments)

        channel.exchange_declare.assert_called_with(exchange_name, type_name,
                                                    passive, durable,
                                                    auto_delete, no_wait,
                                                    arguments)

    async def test_publish(self):
        payload = "payload"
        exchange_name = "name"
        routing_key = "key"
        properties = object()
        channel = mock.MagicMock()
        channel.publish = mock.CoroutineMock()
        self.broker._get_channel = mock.CoroutineMock(return_value=channel)

        await self.broker.publish(payload, exchange_name, routing_key,
                                  properties)

        channel.publish.assert_called_with(payload, exchange_name, routing_key,
                                           properties)

    async def test_publish_on_connection_error(self):
        payload = "payload"
        exchange_name = "name"
        routing_key = "key"
        properties = object()
        channel = mock.MagicMock()
        error = ConnectionError("message")
        channel.publish = mock.CoroutineMock(side_effect=error)
        self.broker._get_channel = mock.CoroutineMock(return_value=channel)

        with self.assertRaisesRegex(NetworkError, str(error)):
            await self.broker.publish(payload, exchange_name, routing_key,
                                      properties)

        channel.publish.assert_called_with(payload, exchange_name, routing_key,
                                           properties)

    async def test_close(self):
        self.broker._transport = mock.MagicMock()
        self.broker._protocol = mock.MagicMock()
        self.broker._protocol.close = mock.CoroutineMock()
        self.broker._protocol.connection_closed.is_set.return_value = False

        await self.broker.close()

        self.broker._transport.close.assert_called()
        self.broker._protocol.close.assert_called()

    async def test_close_if_already_closed(self):
        self.broker._transport = mock.MagicMock()
        self.broker._protocol = mock.MagicMock()
        self.broker._protocol.close = mock.CoroutineMock()
        self.broker._protocol.connection_closed.is_set.return_value = True

        await self.broker.close()

        self.broker._transport.close.assert_not_called()
        self.broker._protocol.close.assert_not_called()
