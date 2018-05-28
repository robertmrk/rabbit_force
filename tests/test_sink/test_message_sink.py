from asynctest import TestCase, mock

from rabbit_force.sink.message_sink import AmqpBrokerMessageSink, \
    MultiMessageSink
from rabbit_force.exceptions import MessageSinkError, NetworkError


class TestAmqpMessageSink(TestCase):
    def setUp(self):
        self.broker = mock.MagicMock()
        self.json_dumps = mock.MagicMock()
        self.sink = AmqpBrokerMessageSink(self.broker, self.json_dumps)

    def test_init(self):
        self.assertIs(self.sink.broker, self.broker)
        self.assertIs(self.sink._json_dumps, self.json_dumps)
        self.assertIsNone(self.sink.channel)

    async def test_consume_message(self):
        message = {"foo": "bar"}
        sink_name = "sink name"
        exchange_name = "exchange name"
        routing_key = "routing key"
        properties = {
            "foo": "bar",
            "content_type": "text/html",
            "content_encoding": "gzip"
        }
        encoded_message = object()
        unencoded_message = mock.MagicMock()
        unencoded_message.encode.return_value = encoded_message
        self.json_dumps.return_value = unencoded_message
        self.broker.publish = mock.CoroutineMock()

        await self.sink.consume_message(message, sink_name, exchange_name,
                                        routing_key, properties)

        expected_properties = properties.copy()
        expected_properties["content_type"] = self.sink.CONTENT_TYPE
        expected_properties["content_encoding"] = self.sink.ENCODING
        self.json_dumps.assert_called_with(message)
        unencoded_message.encode.assert_called_with(self.sink.ENCODING)
        self.broker.publish.assert_called_with(encoded_message, exchange_name,
                                               routing_key,
                                               properties=expected_properties)

    async def test_consume_message_without_properties(self):
        message = {"foo": "bar"}
        sink_name = "sink name"
        exchange_name = "exchange name"
        routing_key = "routing key"
        properties = None
        encoded_message = object()
        unencoded_message = mock.MagicMock()
        unencoded_message.encode.return_value = encoded_message
        self.json_dumps.return_value = unencoded_message
        self.broker.publish = mock.CoroutineMock()

        await self.sink.consume_message(message, sink_name, exchange_name,
                                        routing_key, properties)

        expected_properties = {}
        expected_properties["content_type"] = self.sink.CONTENT_TYPE
        expected_properties["content_encoding"] = self.sink.ENCODING
        self.json_dumps.assert_called_with(message)
        unencoded_message.encode.assert_called_with(self.sink.ENCODING)
        self.broker.publish.assert_called_with(encoded_message, exchange_name,
                                               routing_key,
                                               properties=expected_properties)

    async def test_close(self):
        self.broker.close = mock.CoroutineMock()

        await self.sink.close()

        self.broker.close.assert_called()


class TestMultiMessageSink(TestCase):
    def setUp(self):
        self.sinks = {
            "sink1": mock.MagicMock(),
            "sink2": mock.MagicMock()
        }
        self.sink = MultiMessageSink(self.sinks, loop=self.loop)

    def test_init(self):
        self.assertEqual(self.sink.sinks, self.sinks)
        self.assertIs(self.sink._loop, self.loop)

    async def test_consume_message(self):
        message = {"foo": "bar"}
        sink_name = "sink1"
        exchange_name = "exchange name"
        routing_key = "routing key"
        properties = {
            "foo": "bar",
            "content_type": "text/html",
            "content_encoding": "gzip"
        }
        self.sinks["sink1"].consume_message = mock.CoroutineMock()

        await self.sink.consume_message(message, sink_name, exchange_name,
                                        routing_key, properties)

        self.sinks[sink_name].consume_message.assert_called_with(
            message, sink_name, exchange_name, routing_key, properties
        )

    async def test_consume_message_missink_sink(self):
        message = {"foo": "bar"}
        sink_name = "non_existant"
        exchange_name = "exchange name"
        routing_key = "routing key"
        properties = {
            "foo": "bar",
            "content_type": "text/html",
            "content_encoding": "gzip"
        }

        with self.assertRaisesRegex(MessageSinkError,
                                    f"Sink named {sink_name!r} "
                                    f"doesn't exists"):
            await self.sink.consume_message(message, sink_name, exchange_name,
                                            routing_key, properties)

    async def test_consume_message_on_network_error(self):
        message = {"foo": "bar"}
        sink_name = "sink1"
        exchange_name = "exchange name"
        routing_key = "routing key"
        properties = {
            "foo": "bar",
            "content_type": "text/html",
            "content_encoding": "gzip"
        }
        error = NetworkError("message")
        self.sinks[sink_name].consume_message = mock.CoroutineMock(
            side_effect=error
        )

        with self.assertRaisesRegex(MessageSinkError,
                                    f"Network error: {error!s}"):
            await self.sink.consume_message(message, sink_name, exchange_name,
                                            routing_key, properties)

    async def test_close(self):
        for sink in self.sinks.values():
            sink.close = mock.CoroutineMock()

        await self.sink.close()

        for sink in self.sinks.values():
            sink.close.assert_called()
