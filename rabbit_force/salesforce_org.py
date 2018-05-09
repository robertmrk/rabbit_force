"""Class definitions for representing Salesforce orgs"""
from aiosfstream import PasswordAuthenticator
from simple_salesforce import Salesforce as RestClient

from .streaming_resources import StreamingResourceFactory


class SalesforceOrg:
    """Represents a Salesforce org, capable of managing streaming resources"""
    def __init__(self, consumer_key, consumer_secret, username, password):
        """
        :param str consumer_key: Consumer key from the Salesforce connected \
        app definition
        :param str consumer_secret: Consumer secret from the Salesforce \
        connected app definition
        :param str username: Salesforce username
        :param str password: Salesforce password
        """
        #: An authenticator object for storing authentication credentials and \
        #: and providing access tokens
        self.authenticator = PasswordAuthenticator(
            consumer_key,
            consumer_secret,
            username,
            password
        )
        #: Dictionary of available streaming resources by name
        self.resources = {}
        #: Salesforce REST API client
        self._rest_client = None

    async def _get_client(self):
        """Get a Salesforce REST API client object

        :return: REST API client object
        :rtype: simple_salesforce.Salesforce
        """
        # if the client doesn't exists then create it, otherwise return the
        # existing object
        if not self._rest_client:
            await self.authenticator.authenticate()
            self._rest_client = RestClient(
                instance_url=self.authenticator.instance_url,
                session_id=self.authenticator.access_token
            )
        return self._rest_client

    async def add_resource(self, resource_type, resource_spec, durable=True):
        """Add a streaming resource to the Salesforce org

        :param StreamingResourceType resource_type: The type of the resource
        :param dict resource_spec: A resource specification, which either \
        contains all attributes required for creating the resource, or \
        contains a single unique identifier of an existing resource, such as \
        ``Name`` or ``Id``
        :param durable: Whether the resource should be deleted or should \
        it be left on the server after it's no longer in use
        :return: A streaming resource
        :rtype: StreamingResource
        """
        # create the resource factory
        rest_client = await self._get_client()
        factory = StreamingResourceFactory(resource_type, rest_client)

        # create the resource and set the durability
        resource = factory.get_resource(resource_spec)
        resource.durable = durable

        # store the resource by name
        self.resources[resource.name] = resource
        return resource

    async def remove_resource(self, resource):
        """Remove the streaming *resource*

        :param StreamingResource resource: A streaming resource
        """
        # get the client and resource specific client
        rest_client = await self._get_client()
        resource_client = getattr(rest_client, resource.type_name)

        # delete the resource with the given id from the org
        resource_client.delete(resource.id)

    async def cleanup_resources(self):
        """Remove streaming resources which are not marked as durable"""
        non_durable_resources = [res for res in self.resources.values()
                                 if not res.durable]
        for resource in non_durable_resources:
            await self.remove_resource(resource)
