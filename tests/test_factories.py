from asynctest import TestCase, mock
from aiosfstream import ReplayOption

from rabbit_force.factories import create_salesforce_org, \
    create_message_source, create_broker, create_message_sink


class TestCreateSalesforceOrg(TestCase):
    @mock.patch("rabbit_force.factories.SalesforceOrg")
    async def test_create(self, org_cls):
        consumer_key = "key"
        consumer_secret = "secret"
        username = "username"
        password = "password"
        resource_spec = {"key": "value"}
        streaming_resource_specs = [resource_spec]
        org_mock = mock.MagicMock()
        org_mock.add_resource = mock.CoroutineMock()
        org_cls.return_value = org_mock

        result = await create_salesforce_org(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            username=username,
            password=password,
            streaming_resource_specs=streaming_resource_specs,
            loop=self.loop
        )

        self.assertIs(result, org_mock)
        org_cls.assert_called_with(
            consumer_key,
            consumer_secret,
            username,
            password,
            loop=self.loop
        )
        org_mock.add_resource.assert_called_with(**resource_spec)


class TestCreateMessageSource(TestCase):
    @mock.patch("rabbit_force.factories.RedisReplayStorage")
    @mock.patch("rabbit_force.factories.MultiMessageSource")
    @mock.patch("rabbit_force.factories.SalesforceOrgMessageSource")
    async def test_create(self, org_source_cls, multi_source_cls, replay_cls):
        org_specs = {
            "org_name1": {
                "key1": "value1"
            },
            "org_name2": {
                "key2": "value2"
            }
        }
        replay_spec = {"key": "value"}
        org1 = object()
        org2 = object()
        org_factory = mock.CoroutineMock(side_effect=[org1, org2])
        replay_marker_storage = object()
        replay_cls.return_value = replay_marker_storage
        org_source1 = object()
        org_source2 = object()
        org_source_cls.side_effect = [org_source1, org_source2]

        result = await create_message_source(
            org_specs=org_specs,
            replay_spec=replay_spec,
            org_factory=org_factory,
            loop=self.loop
        )

        self.assertIs(result, multi_source_cls.return_value)
        replay_cls.assert_called_with(**replay_spec, loop=self.loop)
        org_factory.assert_has_calls([
            mock.call(**org_specs["org_name1"]),
            mock.call(**org_specs["org_name2"])
        ])
        org_source_cls.assert_has_calls([
            mock.call("org_name1", org1, replay_marker_storage,
                      ReplayOption.ALL_EVENTS, loop=self.loop),
            mock.call("org_name2", org2, replay_marker_storage,
                      ReplayOption.ALL_EVENTS, loop=self.loop)
        ])
        multi_source_cls.assert_called_with([org_source1, org_source2],
                                            loop=self.loop)

    @mock.patch("rabbit_force.factories.RedisReplayStorage")
    @mock.patch("rabbit_force.factories.MultiMessageSource")
    @mock.patch("rabbit_force.factories.SalesforceOrgMessageSource")
    async def test_create_single_source(self, org_source_cls, multi_source_cls,
                                        replay_cls):
        org_specs = {
            "org_name1": {
                "key1": "value1"
            }
        }
        replay_spec = {"key": "value"}
        org1 = object()
        org_factory = mock.CoroutineMock(side_effect=[org1])
        replay_marker_storage = object()
        replay_cls.return_value = replay_marker_storage
        org_source1 = object()
        org_source_cls.side_effect = [org_source1]

        result = await create_message_source(
            org_specs=org_specs,
            replay_spec=replay_spec,
            org_factory=org_factory,
            loop=self.loop
        )

        self.assertIs(result, org_source1)
        replay_cls.assert_called_with(**replay_spec, loop=self.loop)
        org_factory.assert_has_calls([
            mock.call(**org_specs["org_name1"])
        ])
        org_source_cls.assert_has_calls([
            mock.call("org_name1", org1, replay_marker_storage,
                      ReplayOption.ALL_EVENTS, loop=self.loop)
        ])
        multi_source_cls.assert_not_called()

    @mock.patch("rabbit_force.factories.RedisReplayStorage")
    @mock.patch("rabbit_force.factories.MultiMessageSource")
    @mock.patch("rabbit_force.factories.SalesforceOrgMessageSource")
    async def test_create_without_replay_spec(self, org_source_cls,
                                              multi_source_cls, replay_cls):
        org_specs = {
            "org_name1": {
                "key1": "value1"
            },
            "org_name2": {
                "key2": "value2"
            }
        }
        replay_spec = None
        org1 = object()
        org2 = object()
        org_factory = mock.CoroutineMock(side_effect=[org1, org2])
        replay_marker_storage = None
        replay_cls.return_value = replay_marker_storage
        org_source1 = object()
        org_source2 = object()
        org_source_cls.side_effect = [org_source1, org_source2]

        result = await create_message_source(
            org_specs=org_specs,
            replay_spec=replay_spec,
            org_factory=org_factory,
            loop=self.loop
        )

        self.assertIs(result, multi_source_cls.return_value)
        replay_cls.assert_not_called()
        org_factory.assert_has_calls([
            mock.call(**org_specs["org_name1"]),
            mock.call(**org_specs["org_name2"])
        ])
        org_source_cls.assert_has_calls([
            mock.call("org_name1", org1, replay_marker_storage,
                      None, loop=self.loop),
            mock.call("org_name2", org2, replay_marker_storage,
                      None, loop=self.loop)
        ])
        multi_source_cls.assert_called_with([org_source1, org_source2],
                                            loop=self.loop)


class TestCreateBroker(TestCase):
    @mock.patch("rabbit_force.factories.aioamqp")
    async def test_create(self, aioamqp_mod):
        host = "host"
        exchange_specs = [{"key": "value"}]
        port = 1234
        login = "login"
        password = "password"
        virtualhost = "virt_host"
        ssl = True
        login_method = "plain"
        insist = True
        verify_ssl = True
        transport = object()
        channel = mock.MagicMock()
        channel.exchange_declare = mock.CoroutineMock()
        protocol = mock.MagicMock()
        protocol.channel = mock.CoroutineMock(return_value=channel)
        aioamqp_mod.connect = mock.CoroutineMock(
            return_value=(transport, protocol)
        )

        result = await create_broker(
            host=host,
            exchange_specs=exchange_specs,
            port=port,
            login=login,
            password=password,
            virtualhost=virtualhost,
            ssl=ssl,
            login_method=login_method,
            insist=insist,
            verify_ssl=verify_ssl,
            loop=self.loop
        )

        self.assertEqual(result, (transport, protocol))
        aioamqp_mod.connect.assert_called_with(
            host, port, login, password, virtualhost, ssl, login_method,
            insist, verify_ssl=verify_ssl, loop=self.loop
        )
        channel.exchange_declare.assert_called_with(**exchange_specs[0])


class TestCreateMessageSink(TestCase):
    @mock.patch("rabbit_force.factories.MultiMessageSink")
    async def test_create(self, multi_sink_cls):
        broker_specs = {
            "broker1": {
                "key": "value"
            }
        }
        broker = (object(), object())
        broker_factory = mock.CoroutineMock(return_value=broker)
        message_sink = object()
        broker_sink_factory = mock.MagicMock(return_value=message_sink)

        result = await create_message_sink(
            broker_specs=broker_specs,
            broker_factory=broker_factory,
            broker_sink_factory=broker_sink_factory,
            loop=self.loop
        )

        self.assertIs(result, multi_sink_cls.return_value)
        broker_factory.assert_called_with(**broker_specs["broker1"],
                                          loop=self.loop)
        broker_sink_factory.assert_called_with(*broker)
        multi_sink_cls.assert_called_with(
            {"broker1": message_sink}, loop=self.loop
        )
