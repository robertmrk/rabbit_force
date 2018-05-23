"""Factory functions for creating objects from the configuration"""
from aiosfstream import ReplayOption
import aioamqp

from .source.message_source import SalesforceOrgMessageSource, \
    MultiMessageSource, RedisReplayStorage
from .source.salesforce import SalesforceOrg
from .sink.message_sink import AmqpMessageSink, MultiMessageSink


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


async def create_message_source(*, org_specs, replay_spec=None,
                                org_factory=create_salesforce_org, loop=None):
    """Create a message source that wraps the salesforce org defined by
    *org_specs*

    :param dict org_specs: Dictionary of name - Salesforce org specification \
    pairs that can be passed to *org_factory* to create an object
    :param replay_spec: Replay storage specification that can be passed \
    to :obj:`RedisReplayStorage` to create a replay marker storage object
    :type replay_spec: dict or None
    :param callable org_factory: A callable capable of creating a Salesforce \
    org from the items of *org_specs*
    :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                 schedule tasks. If *loop* is ``None`` then
                 :func:`asyncio.get_event_loop` is used to get the default
                 event loop.
    :return: A message source object
    :rtype: ~source.message_source.MessageSource
    """
    # initially assume that there is no replay storage defined and no
    # replay_spec fallback is used
    replay_marker_storage = None
    replay_fallback = None

    # if the replay storage is defined then create it from the specification
    # and use ReplayOption.ALL_EVENTS as the replay_spec fallback
    if replay_spec:
        replay_marker_storage = RedisReplayStorage(**replay_spec, loop=loop)
        replay_fallback = ReplayOption.ALL_EVENTS

    # create the specified Salesforce orgs identified by their names
    salesforce_orgs = {name: await org_factory(**spec)
                       for name, spec in org_specs.items()}

    # create message sources for every Salesforce org object and use the
    # specified replay_spec marker storage and replay_spec fallback values
    message_sources = [SalesforceOrgMessageSource(name, org,
                                                  replay_marker_storage,
                                                  replay_fallback,
                                                  loop=loop)
                       for name, org in salesforce_orgs.items()]

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
    :return: a tuple (transport, protocol) of an AmqpProtocol instance
    :rtype: tuple[asyncio.BaseTransport, aioamqp.protocol.AmqpProtocol]
    """
    # connect to the broker and create the transport and protocol objects
    transport, protocol = await aioamqp.connect(host, port, login, password,
                                                virtualhost, ssl, login_method,
                                                insist, verify_ssl=verify_ssl,
                                                loop=loop)

    # create a channel and declare the exchanges
    channel = await protocol.channel()
    for spec in exchange_specs:
        await channel.exchange_declare(**spec)

    # return the connections transport and protocol
    return transport, protocol


async def create_message_sink(*, broker_specs,
                              broker_factory=create_broker,
                              broker_sink_factory=AmqpMessageSink,
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
    message_sinks = {name: broker_sink_factory(*broker)
                     for name, broker in brokers.items()}

    # group the message sink objects into a multi message sink object
    return MultiMessageSink(message_sinks, loop=loop)
