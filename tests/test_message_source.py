import asyncio

from asynctest import TestCase, mock
from aiosfstream.exceptions import ClientInvalidOperation, AiosfstreamException

from rabbit_force.message_source import SalesforceOrgMessageSource, \
    MultiMessageSource
from rabbit_force.exceptions import InvalidOperation, StreamingError


class TestSalesforceOrgMessageSource(TestCase):
    @mock.patch("rabbit_force.message_source.Client")
    def setUp(self, client_cls):
        self.name = "name"
        self.client = mock.MagicMock()
        client_cls.return_value = self.client
        self.client_cls = client_cls
        self.org = mock.MagicMock()
        self.org.authenticator = mock.MagicMock()
        self.source = SalesforceOrgMessageSource(self.name, self.org)

    def test_init(self):
        self.assertEqual(self.source.name, self.name)
        self.client_cls.assert_called_with(self.org.authenticator,
                                           connection_timeout=0)
        self.assertEqual(self.source.client, self.client)
        self.assertEqual(self.source.salesforce_org, self.org)

    def test_closed(self):
        self.assertIs(self.source.closed, self.client.closed)

    def test_pending_count(self):
        self.assertIs(self.source.pending_count, self.client.pending_count)

    def test_has_pending_messages(self):
        self.assertIs(self.source.has_pending_messages,
                      self.client.has_pending_messages)

    async def test_open(self):
        resource = mock.MagicMock()
        resource.channel_name = "channel_name"
        self.client.open = mock.CoroutineMock()
        self.client.subscribe = mock.CoroutineMock()
        self.org.resources = {"resource": resource}

        await self.source.open()

        self.client.open.assert_called()
        self.client.subscribe.assert_called_with(resource.channel_name)

    async def test_close(self):
        self.client.close = mock.CoroutineMock()
        self.org.cleanup_resources = mock.CoroutineMock()
        self.org.close = mock.CoroutineMock()

        await self.source.close()

        self.client.close.assert_called()
        self.org.cleanup_resources.assert_called()
        self.org.close.assert_called()

    async def test_get_message(self):
        message = object()
        self.client.receive = mock.CoroutineMock(return_value=message)

        result = await self.source.get_message()

        self.assertEqual(result, (self.name, message))
        self.client.receive.assert_called()

    async def test_get_message_if_client_closed(self):
        error = ClientInvalidOperation()
        self.client.receive = mock.CoroutineMock(side_effect=error)

        with self.assertRaisesRegex(InvalidOperation, str(error)):
            await self.source.get_message()

        self.client.receive.assert_called()

    async def test_get_message_streaming_error(self):
        error = AiosfstreamException()
        self.client.receive = mock.CoroutineMock(side_effect=error)

        with self.assertRaisesRegex(StreamingError, str(error)):
            await self.source.get_message()

        self.client.receive.assert_called()


class TestMultiMessageSource(TestCase):
    def setUp(self):
        self.sub_source1 = mock.CoroutineMock()
        self.sub_source2 = mock.CoroutineMock()
        self.source = MultiMessageSource([self.sub_source1, self.sub_source2])

    def test_init(self):
        self.assertEqual(self.source.sources, [self.sub_source1,
                                               self.sub_source2])
        self.assertTrue(self.source.closed)

    def test_closed(self):
        self.assertIs(self.source.closed, self.source._closed)

    def test_pending_count(self):
        self.sub_source1.pending_count = 1
        self.sub_source2.pending_count = 2

        result = self.source.pending_count

        self.assertEqual(result,
                         self.sub_source1.pending_count +
                         self.sub_source2.pending_count)

    def test_has_pending_messages_on_zero_count(self):
        self.sub_source1.pending_count = 0
        self.sub_source2.pending_count = 0

        self.assertFalse(self.source.has_pending_messages)

    def test_has_pending_messages_on_non_zero_count(self):
        self.sub_source1.pending_count = 1
        self.sub_source2.pending_count = 0

        self.assertTrue(self.source.has_pending_messages)

    async def test_open(self):
        self.sub_source1.open = mock.CoroutineMock()
        self.sub_source2.open = mock.CoroutineMock()

        await self.source.open()

        self.sub_source1.open.assert_called()
        self.sub_source2.open.assert_called()
        self.assertFalse(self.source.closed)

    async def test_close(self):
        self.sub_source1.close = mock.CoroutineMock()
        self.sub_source2.close = mock.CoroutineMock()

        await self.source.close()

        self.sub_source1.close.assert_called()
        self.sub_source2.close.assert_called()
        self.assertTrue(self.source.closed)

    async def test_get_message(self):
        sleep_task = asyncio.ensure_future(asyncio.sleep(10))
        result_value = object()
        result_task = asyncio.ensure_future(asyncio.sleep(0, result_value))
        self.sub_source1.closed = False
        self.sub_source2.closed = False

        with mock.patch("rabbit_force.message_source.asyncio.ensure_future") \
                as ensure_future:
            ensure_future.side_effect = [sleep_task, result_task]

            result = await self.source.get_message()

        self.assertEqual(result, result_value)
        with self.assertRaises(asyncio.CancelledError):
            await sleep_task

    async def test_get_message_cancelled(self):
        sleep_task = asyncio.ensure_future(asyncio.sleep(10))
        result_value = object()
        result_task = asyncio.ensure_future(asyncio.sleep(0, result_value))
        self.sub_source1.closed = False
        self.sub_source2.closed = False

        with mock.patch("rabbit_force.message_source."
                        "asyncio.ensure_future") as ensure_future, \
                mock.patch("rabbit_force.message_source."
                           "asyncio.wait") as wait:
            ensure_future.side_effect = [sleep_task, result_task]
            wait.side_effect = asyncio.CancelledError()

            with self.assertRaises(asyncio.CancelledError):
                await self.source.get_message()

        with self.assertRaises(asyncio.CancelledError):
            await sleep_task
        with self.assertRaises(asyncio.CancelledError):
            await result_task
