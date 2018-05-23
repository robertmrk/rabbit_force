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
