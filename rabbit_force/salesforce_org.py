"""Class definitions for representing Salesforce orgs"""
from aiosfstream import PasswordAuthenticator

from .streaming_resources import StreamingResourceFactory
from .salesforce_api import SalesforceApi


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
        self._rest_client = SalesforceApi(self.authenticator)
        # Resource _resource_factory
        self._resource_factory = StreamingResourceFactory(self._rest_client)

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
        # create the resource and set the durability
        resource = await self._resource_factory.create_resource(resource_type,
                                                                resource_spec)
        resource.durable = durable

        # store the resource by name
        self.resources[resource.name] = resource
        return resource

    async def remove_resource(self, resource):
        """Remove the streaming *resource*

        :param StreamingResource resource: A streaming resource
        """
        # delete the resource with the given id from the org
        self._rest_client.delete(resource.type_name, resource.id)

    async def cleanup_resources(self):
        """Remove streaming resources which are not marked as durable"""
        non_durable_resources = [res for res in self.resources.values()
                                 if not res.durable]
        for resource in non_durable_resources:
            await self.remove_resource(resource)

    async def close(self):
        """Close the Salesforce org

        This method should be called when the client finished all interaction
        with the object.
        """
        await self._rest_client.close()
