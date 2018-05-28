import asyncio

from asynctest import TestCase, mock
from aiosfstream.exceptions import ClientInvalidOperation, AiosfstreamException

from rabbit_force.source.message_source import SalesforceOrgMessageSource, \
    MultiMessageSource, RedisReplayStorage
from rabbit_force.exceptions import InvalidOperation, StreamingError


class TestSalesforceOrgMessageSource(TestCase):
    @mock.patch("rabbit_force.source.message_source.Client")
    def setUp(self, client_cls):
        self.name = "name"
        self.client = mock.MagicMock()
        client_cls.return_value = self.client
        self.client_cls = client_cls
        self.org = mock.MagicMock()
        self.org.authenticator = mock.MagicMock()
        self.replay = object()
        self.replay_fallback = object()
        self.source = SalesforceOrgMessageSource(
            self.name,
            self.org,
            replay=self.replay,
            replay_fallback=self.replay_fallback,
            loop=self.loop
        )

    def test_init(self):
        self.assertEqual(self.source.name, self.name)
        self.client_cls.assert_called_with(
            self.org.authenticator,
            replay=self.replay,
            replay_fallback=self.replay_fallback,
            connection_timeout=0,
            loop=self.loop
        )
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
        self.source = MultiMessageSource([self.sub_source1, self.sub_source2],
                                         loop=self.loop)

    def test_init(self):
        self.assertEqual(self.source.sources, [self.sub_source1,
                                               self.sub_source2])
        self.assertEqual(self.source._loop, self.loop)
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

        with mock.patch("rabbit_force.source.message_source."
                        "asyncio.ensure_future") as ensure_future:
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

        with mock.patch("rabbit_force.source.message_source."
                        "asyncio.ensure_future") as ensure_future, \
                mock.patch("rabbit_force.source.message_source."
                           "asyncio.wait") as wait:
            ensure_future.side_effect = [sleep_task, result_task]
            wait.side_effect = asyncio.CancelledError()

            with self.assertRaises(asyncio.CancelledError):
                await self.source.get_message()

        with self.assertRaises(asyncio.CancelledError):
            await sleep_task
        with self.assertRaises(asyncio.CancelledError):
            await result_task


class TestRedisReplayStorage(TestCase):
    def setUp(self):
        self.address = "address"
        self.prefix = None
        self.additional_params = {"foo": "bar"}
        self.replay = RedisReplayStorage(self.address, key_prefix=self.prefix,
                                         loop=self.loop,
                                         **self.additional_params)

    def test_init(self):
        self.assertEqual(self.replay.address, self.address)
        self.assertEqual(self.replay.key_prefix, "")
        self.assertEqual(self.replay.additional_params, self.additional_params)
        self.assertEqual(self.replay._loop, self.loop)
        self.assertIsNone(self.replay._redis)

    def test_get_key(self):
        self.replay.key_prefix = "prefix"
        subscription = "subscription"

        result = self.replay._get_key(subscription)

        self.assertEqual(result, self.replay.key_prefix + ":" + subscription)

    @mock.patch("rabbit_force.source.message_source."
                "aioredis.create_redis_pool")
    async def test_get_redis(self, create_redis_pool):
        result = await self.replay._get_redis()

        self.assertEqual(result, create_redis_pool.return_value)
        self.assertEqual(self.replay._redis, create_redis_pool.return_value)
        create_redis_pool.assert_called_with(self.replay.address,
                                             loop=self.loop,
                                             **self.additional_params)

    @mock.patch("rabbit_force.source.message_source."
                "aioredis.create_redis_pool")
    async def test_get_redis_if_exists(self, create_redis_pool):
        self.replay._redis = object()

        result = await self.replay._get_redis()

        self.assertEqual(result, self.replay._redis)
        create_redis_pool.assert_not_called()

    @mock.patch("rabbit_force.source.message_source.pickle.loads")
    async def test_get_replay_marker(self, pickle_loads):
        redis = mock.MagicMock()
        key = "key"
        self.replay._get_redis = mock.CoroutineMock(return_value=redis)
        self.replay._get_key = mock.MagicMock(return_value=key)
        serialized_value = object()
        redis.get = mock.CoroutineMock(return_value=serialized_value)
        deserialized_value = object()
        pickle_loads.return_value = deserialized_value
        subscription = "subscription"

        result = await self.replay.get_replay_marker(subscription)

        self.assertEqual(result, deserialized_value)
        self.replay._get_key.assert_called_with(subscription)
        redis.get.assert_called_with(key)
        pickle_loads.assert_called_with(serialized_value)

    @mock.patch("rabbit_force.source.message_source.pickle.loads")
    async def test_get_replay_marker_value_none(self, pickle_loads):
        redis = mock.MagicMock()
        key = "key"
        self.replay._get_redis = mock.CoroutineMock(return_value=redis)
        self.replay._get_key = mock.MagicMock(return_value=key)
        serialized_value = None
        redis.get = mock.CoroutineMock(return_value=serialized_value)
        deserialized_value = object()
        pickle_loads.return_value = deserialized_value
        subscription = "subscription"

        result = await self.replay.get_replay_marker(subscription)

        self.assertIsNone(result)
        self.replay._get_key.assert_called_with(subscription)
        redis.get.assert_called_with(key)
        pickle_loads.assert_not_called()

    @mock.patch("rabbit_force.source.message_source.pickle.loads")
    async def test_get_replay_marker_on_connection_error(self, pickle_loads):
        redis = mock.MagicMock()
        key = "key"
        self.replay._get_redis = mock.CoroutineMock(return_value=redis)
        self.replay._get_key = mock.MagicMock(return_value=key)
        error = ConnectionError("message")
        redis.get = mock.CoroutineMock(side_effect=error)
        deserialized_value = object()
        pickle_loads.return_value = deserialized_value
        subscription = "subscription"

        with self.assertLogs(RedisReplayStorage.__module__, "ERROR") as log:
            result = await self.replay.get_replay_marker(subscription)

        self.assertIsNone(result)
        self.replay._get_key.assert_called_with(subscription)
        redis.get.assert_called_with(key)
        self.assertEqual(log.output, [
            f"ERROR:{RedisReplayStorage.__module__}:"
            f"Failed to get the replay marker from redis for "
            f"subscription {subscription!r}. {error!s}"
        ])

    @mock.patch("rabbit_force.source.message_source.pickle.dumps")
    async def test_set_replay_marker(self, pickle_dumps):
        redis = mock.MagicMock()
        key = "key"
        self.replay._get_redis = mock.CoroutineMock(return_value=redis)
        self.replay._get_key = mock.MagicMock(return_value=key)
        serialized_value = object()
        deserialized_value = object()
        redis.set = mock.CoroutineMock()
        pickle_dumps.return_value = serialized_value
        subscription = "subscription"

        await self.replay.set_replay_marker(subscription, deserialized_value)

        self.replay._get_key.assert_called_with(subscription)
        pickle_dumps.assert_called_with(deserialized_value)
        redis.set.assert_called_with(key, serialized_value)

    @mock.patch("rabbit_force.source.message_source.pickle.dumps")
    async def test_set_replay_marker_on_connection_error(self, pickle_dumps):
        redis = mock.MagicMock()
        key = "key"
        self.replay._get_redis = mock.CoroutineMock(return_value=redis)
        self.replay._get_key = mock.MagicMock(return_value=key)
        serialized_value = object()
        deserialized_value = object()
        error = ConnectionError("message")
        redis.set = mock.CoroutineMock(side_effect=error)
        pickle_dumps.return_value = serialized_value
        subscription = "subscription"

        with self.assertLogs(RedisReplayStorage.__module__, "ERROR") as log:
            await self.replay.set_replay_marker(subscription,
                                                deserialized_value)

        self.replay._get_key.assert_called_with(subscription)
        pickle_dumps.assert_called_with(deserialized_value)
        redis.set.assert_called_with(key, serialized_value)
        self.assertEqual(log.output, [
            f"ERROR:{RedisReplayStorage.__module__}:"
            f"Failed to set the replay marker in redis for "
            f"subscription {subscription!r}. {error!s}"
        ])
