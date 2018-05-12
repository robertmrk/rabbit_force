from asynctest import TestCase, mock

from rabbit_force.sink.message_sink import AmqpMessageSink, MultiMessageSink


class TestAmqpMessageSink(TestCase):
    def setUp(self):
        self.protocol = mock.MagicMock()
        self.transport = mock.MagicMock()
        self.json_dumps = mock.MagicMock()
        self.sink = AmqpMessageSink(self.transport, self.protocol,
                                    self.json_dumps)

    def test_init(self):
        self.assertIs(self.sink.protocol, self.protocol)
        self.assertIs(self.sink.transport, self.transport)
        self.assertIs(self.sink._json_dumps, self.json_dumps)
        self.assertIsNone(self.sink.channel)

    async def test_get_channel(self):
        self.sink.channel = object()

        result = await self.sink._get_channel()

        self.assertIs(result, self.sink.channel)

    async def test_get_channel_creates_channel(self):
        self.sink.protocol.channel = mock.CoroutineMock()

        result = await self.sink._get_channel()

        self.assertIs(result, self.protocol.channel.return_value)
        self.assertIs(self.sink.channel, self.protocol.channel.return_value)

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
        channel = mock.MagicMock()
        channel.publish = mock.CoroutineMock()
        self.sink._get_channel = mock.CoroutineMock(return_value=channel)

        await self.sink.consume_message(message, sink_name, exchange_name,
                                        routing_key, properties)

        expected_properties = properties.copy()
        expected_properties["content_type"] = self.sink.CONTENT_TYPE
        expected_properties["content_encoding"] = self.sink.ENCODING
        self.json_dumps.assert_called_with(message)
        unencoded_message.encode.assert_called_with(self.sink.ENCODING)
        channel.publish.assert_called_with(encoded_message, exchange_name,
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
        channel = mock.MagicMock()
        channel.publish = mock.CoroutineMock()
        self.sink._get_channel = mock.CoroutineMock(return_value=channel)

        await self.sink.consume_message(message, sink_name, exchange_name,
                                        routing_key, properties)

        expected_properties = {}
        expected_properties["content_type"] = self.sink.CONTENT_TYPE
        expected_properties["content_encoding"] = self.sink.ENCODING
        self.json_dumps.assert_called_with(message)
        unencoded_message.encode.assert_called_with(self.sink.ENCODING)
        channel.publish.assert_called_with(encoded_message, exchange_name,
                                           routing_key,
                                           properties=expected_properties)

    async def test_close(self):
        self.protocol.close = mock.CoroutineMock()

        await self.sink.close()

        self.protocol.close.assert_called()
        self.transport.close.assert_called()


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

    async def test_close(self):
        for sink in self.sinks.values():
            sink.close = mock.CoroutineMock()

        await self.sink.close()

        for sink in self.sinks.values():
            sink.close.assert_called()
