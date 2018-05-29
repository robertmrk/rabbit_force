"""Factory functions for creating objects from the configuration"""
from aiosfstream import ReplayOption

from .source.message_source import SalesforceOrgMessageSource, \
    MultiMessageSource, RedisReplayStorage
from .source.salesforce import SalesforceOrg
from .sink.message_sink import AmqpBrokerMessageSink, MultiMessageSink
from .routing import Route, RoutingRule, RoutingCondition, MessageRouter
from .amqp_broker import AmqpBroker


async def create_salesforce_org(*, consumer_key, consumer_secret, username,
                                password, streaming_resource_specs, loop=None):
    """Create and initialize a Salesforce org with the specified streaming
    resources

    :param str consumer_key: Consumer key from the Salesforce connected \
    app definition
    :param str consumer_secret: Consumer secret from the Salesforce \
    connected app definition
    :param str username: Salesforce username
    :param str password: Salesforce password
    :param list[dict] streaming_resource_specs: List of resource \
    specifications that can be passed to
    :meth:`~source.salesforce.org.SalesforceOrg.add_resource`
    :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                 schedule tasks. If *loop* is ``None`` then
                 :func:`asyncio.get_event_loop` is used to get the default
                 event loop.
    :return: An initialized Salesforce org object
    :rtype: ~source.salesforce.org.SalesforceOrg
    """
    # create the Salesforce org
    org = SalesforceOrg(consumer_key, consumer_secret, username, password,
                        loop=loop)

    # loop through the list of streaming resource specifications
    for spec in streaming_resource_specs:
        # add the resource to the Salesforce org
        await org.add_resource(**spec)

    # return the initialized org
    return org


async def create_replay_storage(*, replay_spec, source_name,
                                ignore_network_errors=False, loop=None):
    """Create a replay marker storage object for the given *source_name*
    based on the *replay_spec*

    :param replay_spec: Replay storage specification that can be passed \
    to :obj:`RedisReplayStorage` to create a replay marker storage object
    :type replay_spec: dict or None
    :param str source_name: Name of the message source
    :param bool ignore_network_errors: If True then no exceptions will \
    be raised in case of a network error occurs in the replay marker storage \
    object
    :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                 schedule tasks. If *loop* is ``None`` then
                 :func:`asyncio.get_event_loop` is used to get the default
                 event loop.
    :return:
    """
    replay_marker_storage = None
    replay_fallback = None

    # if the replay storage is defined
    if replay_spec:
        # append the value of the source_name to the key prefix
        if replay_spec.get("key_prefix"):
            replay_spec["key_prefix"] += ":" + source_name
        else:
            replay_spec["key_prefix"] = source_name

        # create the replay storage from the specification and use
        # ReplayOption.ALL_EVENTS as the replay fallback
        replay_marker_storage = RedisReplayStorage(
            **replay_spec,
            ignore_network_errors=ignore_network_errors,
            loop=loop)
        replay_fallback = ReplayOption.ALL_EVENTS

    return replay_marker_storage, replay_fallback


async def create_message_source(*, org_specs, replay_spec=None,
                                org_factory=create_salesforce_org,
                                replay_storage_factory=create_replay_storage,
                                ignore_replay_storage_errors=False,
                                connection_timeout=10.0,
                                loop=None):
    """Create a message source that wraps the salesforce org defined by
    *org_specs*

    :param dict org_specs: Dictionary of name - Salesforce org specification \
    pairs that can be passed to *org_factory* to create an object
    :param replay_spec: Replay storage specification that can be passed \
    to :obj:`RedisReplayStorage` to create a replay marker storage object
    :type replay_spec: dict or None
    :param callable org_factory: A callable capable of creating a Salesforce \
    org from the items of *org_specs*
    :param callable replay_storage_factory: A callable capable of creating a \
    replay marker storage object from the *replay_spec*
    :param bool ignore_replay_storage_errors: If True then no exceptions will \
    be raised in case of a network error occurs in the replay marker storage \
    object
    :param connection_timeout: The maximum amount of time to wait for the \
    client to re-establish a connection with the server when the \
    connection fails.
    :type connection_timeout: int, float or None
    :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                 schedule tasks. If *loop* is ``None`` then
                 :func:`asyncio.get_event_loop` is used to get the default
                 event loop.
    :return: A message source object
    :rtype: ~source.message_source.MessageSource
    """
    # create the specified Salesforce orgs identified by their names
    salesforce_orgs = {name: await org_factory(**spec)
                       for name, spec in org_specs.items()}

    # create message sources for every Salesforce org object and use the
    # specified replay_spec marker storage and replay_spec fallback values
    message_sources = []
    for name, org in salesforce_orgs.items():
        replay_marker_storage, replay_fallback = await replay_storage_factory(
            replay_spec=replay_spec,
            source_name=name,
            ignore_network_errors=ignore_replay_storage_errors,
            loop=loop
        )
        source = SalesforceOrgMessageSource(name, org,
                                            replay_marker_storage,
                                            replay_fallback,
                                            connection_timeout,
                                            loop=loop)
        message_sources.append(source)

    # if there is only a single org specified, then return the message source
    # that wraps it
    if len(message_sources) == 1:
        return message_sources[0]

    # if multiple org_specs are specified, group their message sources into a
    # multi message source object
    return MultiMessageSource(message_sources, loop=loop)


async def create_broker(*, host, exchange_specs, port=None, login='guest',
                        password='guest', virtualhost='/', ssl=False,
                        login_method='AMQPLAIN', insist=False, verify_ssl=True,
                        loop=None):
    """Create and initialize a message broker with the given parameters

    :param str host: the host to connect to
    :param list[dict] exchange_specs: List of exchange specifications that \
    can be passed to :py:meth:`aioamqp.channel.Channel.exchange_declare`
    :param port: broker port
    :type port: int or None
    :param str login: login
    :param str password: password
    :param str virtualhost: AMQP virtualhost to use for this connection
    :param bool ssl: Create an SSL connection instead of a plain unencrypted \
    one
    :param str login_method: AMQP auth method
    :param bool insist: Insist on connecting to a server
    :param bool verify_ssl: Verify server's SSL certificate (True by default)
    :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                 schedule tasks. If *loop* is ``None`` then
                 :func:`asyncio.get_event_loop` is used to get the default
                 event loop.
    :return: An AMQP broker instance
    :rtype: AmqpBroker
    """
    # create a broker object
    broker = AmqpBroker(host, port=port, login=login, password=password,
                        virtualhost=virtualhost, ssl=ssl,
                        login_method=login_method, insist=insist,
                        verify_ssl=verify_ssl, loop=loop)

    # declare the exchanges
    for spec in exchange_specs:
        await broker.exchange_declare(**spec)

    return broker


async def create_message_sink(*, broker_specs,
                              broker_factory=create_broker,
                              broker_sink_factory=AmqpBrokerMessageSink,
                              loop=None):
    """Create a message sink that wraps the brokers defined by
    *broker_specs*

    :param dict broker_specs: Dictionary of name - broker specification \
    pairs that can be passed to *broker_factory* to create an object
    :param callable broker_factory: A callable capable of creating a message \
    broker from the items of *broker_specs*
    :param callable broker_sink_factory: A callable capable of creating \
    :py:obj:`MessageSink` objects which will wrap broker instances
    :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                 schedule tasks. If *loop* is ``None`` then
                 :func:`asyncio.get_event_loop` is used to get the default
                 event loop.
    :rtype: ~sink.message_sink.MessageSink
    """
    # create the specified broker objects identified by their names
    brokers = {name: await broker_factory(**params, loop=loop)
               for name, params in broker_specs.items()}

    # create message sink for every broker object
    message_sinks = {name: broker_sink_factory(broker)
                     for name, broker in brokers.items()}

    # group the message sink objects into a multi message sink object
    return MultiMessageSink(message_sinks, loop=loop)


def create_rule(*, condition_spec, route_spec,
                condition_factory=RoutingCondition, route_factory=Route):
    """Create a routing rule from *condition_spec* and *route_spec*

    :param str condition_spec: A string that can be used to construct a \
    routing condition using the *condition_factory*
    :param dict route_spec: A dictionary that can be used to construct a \
    route using the *route_factory*
    :param callable condition_factory: A callable capable of creating \
    :py:obj:`RoutingCondition` objects
    :param callable route_factory: A callable capable of creating \
    :py:obj:`Route` objects
    :return: A routing rule object
    :rtype: RoutingRule
    """
    # construct the routing condition and the route
    condition = condition_factory(condition_spec)
    route = route_factory(**route_spec)

    # return the routing rule created with the condition and route
    return RoutingRule(condition, route)


def create_router(*, default_route_spec, rule_specs, route_factory=Route,
                  rule_factory=create_rule):
    """Create a message router from the *default_route_spec* and *rule_specs*

    :param default_route_spec: A dictionary that can be used to \
    construct a route using the *route_factory*
    :type default_route_spec: dict or None
    :param list[dict] rule_specs: A list of dictionaries that can be used \
    to construct routing rules with the *rule_factory*
    :param callable route_factory: A callable capable of creating \
    :py:obj:`Route` objects
    :param rule_factory:  A callable capable of creating \
    :py:obj:`RoutingRule` objects
    :return: A message router object
    :rtype: MessageRouter
    """
    # if there is no default route defined then use None
    default_route = None

    # if a default route is defined then construct it
    if default_route_spec is not None:
        default_route = route_factory(**default_route_spec)

    # construct a list of routing rule objects from the rule specs
    rules = [rule_factory(**spec) for spec in rule_specs]

    # return a message router constructed from the default route and list of
    # routing rules
    return MessageRouter(default_route, rules)
