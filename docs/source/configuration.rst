Configuration
=============

Connections to external services and routing rules are defined using a
configuration files which can be in either in JSON (.json) or in YAML
(.yaml, .yml) format.

There are three main components which should be configured when rabbit_force
is started, likewise the configuration file has three main sections.

* `source`_ - The Salesforce org(s), or in other words message source(s), that
  rabbit_force needs to connect to in order to receive event messages through
  the Streaming API.
* `sink`_ - RabbitMQ broker(s), or in other words message sink(s), to which
  rabbit_force should forward messages using AMQP.
* `router`_ - Routing rules that define to which broker and exchange the
  messages need to be forwarded.

source
------

The `source`_ mapping has two properties, `orgs`_ where the connected
Salesforce orgs can be defined and and an optional `replay`_ property which can
be defined if you want to take advantage of Salesforce's
`message durability <replay_>`_ feature.

orgs
~~~~

The `orgs`_ property's value should be a mapping Salesforce org names and the
orgs' specifications. You can define multiple `name` and `org specification`
pairs, and use the `name` strings in the `router`_ section to refer to specific
Salesforce orgs.

.. code-block:: yaml
    :caption: Multiple Salesforce orgs example

    orgs:
        # a Salesforce org named as "org1"
        org1:
          consumer_key: "<consumer_key1>"
          consumer_secret: "<consumer_secret1>"
          username: "<username1>"
          password: "<password1>"
          resources:
            - type: PushTopic
              spec:
                Name: lead_changes
                ApiVersion: 42.0
                NotifyForFields: Referenced
                NotifyForOperationCreate: true
                NotifyForOperationUpdate: true
                NotifyForOperationDelete: true
                NotifyForOperationUndelete: true
                Query: SELECT Id, Email, Name, Phone, MobilePhone, Status, LeadSource FROM Lead

        # a Salesforce org named as "org2"
        org2:
          consumer_key: "<consumer_key2>"
          consumer_secret: "<consumer_secret2>"
          username: "<username2>"
          password: "<password2>"
          resources:
            - type: PushTopic
              spec:
                Name: contact_changes
                ApiVersion: 42.0
                NotifyForFields: Referenced
                NotifyForOperationCreate: true
                NotifyForOperationUpdate: true
                NotifyForOperationDelete: true
                NotifyForOperationUndelete: true
                Query: SELECT Id, Email, Name, Phone, MobilePhone FROM Contact

The properties of the Salesforce org specification are documented below.

consumer_key
^^^^^^^^^^^^

The `consumer_key's <consumer_key_>`_ value should be the consumer key from
the Salesforce connected app definition.

consumer_secret
^^^^^^^^^^^^^^^

The `consumer_secret's <consumer_secret_>`_ value should be the consumer secret
from the Salesforce connected app definition.

username
^^^^^^^^

The Salesforce user's username as a string.

password
^^^^^^^^

The Salesforce user's password as a string.

resources
^^^^^^^^^

The `resources`_ property's value should be a list of Salesforce REST API
resources, which are capable of generating event messages. For every resource
the `type`_, `spec`_ and optionally the `durable <durable_section_>`_
properties should be defined.

type
""""

The type of the resource should be either `PushTopic <PushTopic spec_>`_ or
`StreamingChannel <StreamingChannel spec_>`_.

spec
""""

A resource specification is a mapping, which should either contain
the full resource definition, which can be used to create the given resource
on the given Salesforce org, or if it's an existing resource, then a single
property should be given which uniquely defines the resource, such as the
``Id`` or the ``Name`` property.

.. code-block:: yaml
    :caption: Existing resource identified by name

    resources:
        - type: PushTopic
          spec:
            Name: lead_changes

If a new resource is defined and the `type`_ of the resource is ``PushTopic``
then the value of the `spec`_ property should conform to the mapping described
in `PushTopic spec`_, if the `type`_ of the resource is ``StreamingChannel``
then the `spec`_ property should conform to `StreamingChannel spec`_.

PushTopic spec
''''''''''''''

When defining a resource of `type`_ ``PushTopic`` then the `spec`_ mapping
can contain exaclty the same value's as defined by `Salesforce's REST API
reference for creating PushTopics <PushTopicRef_>`_.

========================== ============= ======================================
Property                   Property type Description
========================== ============= ======================================
Id                         String        Globally unique string that identifies
                                         a record. The Id
                                         property should be defined
                                         **only when** you're trying to refer
                                         to an existing PushTopic.
Name                       String        Required. Descriptive name of the
                                         PushTopic, such as MyNewCases or
                                         TeamUpdatedContacts. Limit: 25
                                         characters. This value identifies the
                                         channel and must be unique.
ApiVersion                 Float         Required. API version to use for
                                         executing the query specified in Query.
                                         It must be an API version greater than
                                         20.0. If your query applies to a
                                         custom object from a package, this
                                         value must match the package's
                                         ApiVersion.
                                         Example value: 43.0
IsActive                   Boolean       Indicates whether the record currently
                                         counts towards the organization's
                                         allocation.
NotifyForFields            String        Specifies which fields are evaluated
                                         to generate a notification.
                                         Valid values: All, Referenced
                                         (default), Select, Where
Description                String        Description of the PushTopic. Limit:
                                         400 characters
NotifyForOperationCreate   Boolean       true if a create operation should
                                         generate a notification, otherwise,
                                         false. Defaults to true. This field is
                                         available in API version 29.0 and
                                         later.
NotifyForOperationUpdate   Boolean       true if an update operation should
                                         generate a notification, otherwise,
                                         false. Defaults to true. This field is
                                         available in API version 29.0 and
                                         later.
NotifyForOperationDelete   Boolean       true if a delete operation should
                                         generate a notification, otherwise,
                                         false. Defaults to true. This field is
                                         available in API version 29.0 and
                                         later.
NotifyForOperationUndelete Boolean       true if an undelete operation should
                                         generate a notification, otherwise,
                                         false. Defaults to true. This field is
                                         available in API version 29.0 and
                                         later.
NotifyForOperations        String        Specifies which record events may
                                         generate a notification. Valid values:
                                         All (default), Create, Extended,
                                         Update.
                                         In API version 29.0 and later, this
                                         field is read-only, and will not
                                         contain information about delete and
                                         undelete events. Use
                                         NotifyForOperationCreate,
                                         NotifyForOperationDelete,
                                         NotifyForOperationUndelete and
                                         NotifyForOperationUpdate to specify
                                         which record events should generate a
                                         notification.

                                         A value of Extended means that neither
                                         create or update operations are set to
                                         generate events.
Query                      String        Required. The SOQL query statement
                                         that determines which record changes
                                         trigger events to be sent to the
                                         channel. Limit: 1,300 characters
========================== ============= ======================================

StreamingChannel spec
'''''''''''''''''''''

When defining a resource of `type`_ ``StreamingChannel`` then the `spec`_
mapping can contain exaclty the same value's as defined by `Salesforce's REST
API reference for creating StreamingChannels <StreamingChannelRef_>`_.

=========== ============= =====================================================
Property    Property type Description
=========== ============= =====================================================
Id          String        Globally unique string that identifies a
                          StreamingChannel record. The Id property should be
                          defined **only when** you're trying to refer to an
                          existing StreamingChannel.
Name        String        Required. Descriptive name of the StreamingChannel.
                          Limit: 80 characters, alphanumeric and “_”, “/”
                          characters only. Must start with “/u/”. This value
                          identifies the channel and must be unique.
Description String        Description of the StreamingChannel. Limit: 255
                          characters.
=========== ============= =====================================================

.. _durable_section:

durable
"""""""

Durable is an optional property, if ``true`` then the resource will be deleted
when the service is terminated, if ``false`` then the resource will remain on
server after the service is terminated. The default value is ``true``.

replay
~~~~~~

Replay is an optional property which can be specified to take advantage of
the Streaming API's `message durability <replay_>`_ feature.

Salesforce stores events for 24 hours. Events outside the 24-hour retention
period are discarded. Salesforce extends the event messages with `repalyId`
and `createdDate` fields which are called as `ReplayMarkers`. By storing
these `ReplayMarker` values and sending them when subscribing to channels,
message loss can be avoided which might occur due to hardware, software or
network failures.

rabbit_force can store `ReplayMarker` values in a
`Redis <redis_>`_ database. To define the connection to the database the
`address`_ and optionally the `key_prefix`_ properties should be specified.

address
^^^^^^^

The address of the `Redis <redis_>`_ database as a string.

key_prefix
^^^^^^^^^^

A prefix string to add to all keys stored in the database by rabbit_force.

sink
----

The `sink`_ mapping has a single property named `brokers`_ where the connected
RabbitMQ brokers can be defined.

brokers
~~~~~~~

The `brokers`_ property's value should be a mapping RabbitMQ broker
names and the brokers' specifications. You can define multiple `name` and
`broker specification` pairs, and use the `name` strings in the `router`_
section to refer to specific RabbitMQ brokers.

.. code-block:: yaml
    :caption: Multiple RabbitMQ brokers example

    brokers:
        # a RabbitMQ broker named as "broker1"
        broker1:
          host: host1
          exchanges:
            - exchange_name: my_exchange
              type_name: topic
              durable: true

        # a RabbitMQ broker named as "broker2"
        broker2:
          host: host2
          exchanges:
            - exchange_name: my_exchange
              type_name: topic
              durable: true

The properties of the RabbitMQ broker specification are documented below.

host
^^^^

The host name of the broker as a string.

port
^^^^

*Optional* port name of the broker as an integer. If not specified then the
default port number of RabbitMQ will be used which is either ``5672`` if
`ssl`_ is ``false`` or ``5671`` if `ssl`_ is ``true``.

login
^^^^^

*Optional* username as a string. The default value is ``guest``.

password
^^^^^^^^

*Optional* password as a string. The default value is ``guest``.

virtualhost
^^^^^^^^^^^

*Optional* AMQP virtualhost as a string to use for the connection. The default
value is ``/``.

ssl
^^^

*Optional* boolean value. If ``true`` then the service creates an SSL
connection instead of a plain unencrypted one. The default value is ``false``.

verify_ssl
^^^^^^^^^^

*Optional* boolean value. If ``true`` then the server's SSL certificate
will be verified on connection if the `ssl`_ property's value is ``true``. The
default value is ``true``.

login_method
^^^^^^^^^^^^

*Optional* string which defines the AMQP authentication method. The default
value is ``AMQPLAIN``. All the alternative authentication methods are listed
in `RabbitMQ's Authentication <rabbitmq_auth_>`_ documentation.

insist
^^^^^^

*Optional* boolean value. If ``true`` then insist on connecting to a server.
The default value is ``false``.

exchanges
^^^^^^^^^

The `exchanges`_ property's value should be a list of RabbitMQ exchange
definitions. These are the exchanges that can be used in the `router`_ section
by referring to them by their `exchange_name <exchange_name_section_>`_
property.

.. _exchange_name_section:

exchange_name
"""""""""""""

The name of the exchange as a string.

type_name
"""""""""

The exchange's type as a string. The possible values are ``fanout``,
``direct``, ``topic`` and ``headers``. The routing capabilities of the various
exchange types are explained in
`RabbitMQ's documentation <rabbitmq_exchange_type_>`_.

passive
"""""""

*Optional* boolean value. If set, the server will reply with Declare-Ok if
the exchange already exists with the same name, and raise an error if not. The
default value is ``false``.

durable
"""""""

*Optional* boolean value. If set when creating a new exchange, the exchange
will be marked as durable. Durable exchanges remain active when a server
restarts. The default value is ``false``.

auto_delete
"""""""""""

*Optional* boolean value. If set, the exchange is deleted when all queues have
finished using it. The default value is ``false``.

no_wait
"""""""

*Optional* boolean value. If set, the server will not respond to the method.
The default value is ``false``.

arguments
"""""""""

An *Optional* dictionary which can contain
`AMQP arguments <rabbitmq_policies_>`_ to be passed when
creating the exchange. The default value is ``null``.

router
------

The `router`_ section defines how and where to forward incoming messages.

default_route
~~~~~~~~~~~~~

The `default_route`_ property's value should be either a mapping containing
route parameters or ``null``. The `default_route`_ is used to forward messages
without a matching routing rule from the `rules`_ property. If its value is
``null`` then the messages without a matching rule will be dropped.

broker_name
^^^^^^^^^^^

The name of the RabbitMQ broker as a string. Its value should be one of
broker names defined in `brokers`_.

exchange_name
^^^^^^^^^^^^^

The name of the RabbitMQ exchange as a string. Its value should be one of the
`exchange_name`_ properties defined for the broker referred in `broker_name`_.

routing_key
^^^^^^^^^^^

The message's routing key as a string.

properties
^^^^^^^^^^

An *optional* mapping of message properties. RabbitMQ accepts the
``content_type``, ``content_encoding``, ``headers``, ``delivery_mode``,
``priority``, ``correlation_id``, ``reply_to``, ``expiration``, ``message_id``,
``timestamp``, ``type``, ``user_id``, ``app_id`` and ``cluster_id`` properties.
However ``content_type`` and ``content_encoding`` will be overwritten by
rabbit_force so all messages are forwarded with the ``content_type`` of
``application/json`` and with a ``content_encoding`` of ``utf-8``.

rules
~~~~~

The `rules`_ property is an *optional* list of routing rules. Every rule should
contain a `condition`_ and `route`_ property. On receiving a message,
rabbit_force will iterate over the defined routing `rules`_ and will use the
`route`_ from the first matching rule to forward the message. If no matching
rule is found, then the `default_route`_ will be used.

condition
^^^^^^^^^

The `condition`_ property of the routing rule is used to decide whether the
rule should be applied to a given message or not. The value of this property
should be a `JSONPath <jsonpath_>`_ expression as a string. The JSONPath
expression is evaluated on a single element array, where the single element of
the array contains both the source of the message and the message itself. This
way JSONPath filter expressions can be used to match messages.

For example an incoming message such as the one below::

    {
      "channel": "/topic/InvoiceStatementUpdates",
      "data":
      {
        "event":
        {
          "type": "updated",
          "createdDate": "2011-11-03T15:59:06.000+0000"
        },
        "sobject":
        {
          "Name": "INV-0001",
          "Id": "a00D0000008o6y8IAA",
          "Status__c": "Open"
        }
      }
    }

from a Salesforce org named ``org1`` is transformed to the the following array
before evaluating the JSONPath expression on it::

    [
        {
            "org_name": "org1",
            "message":
            {
                "channel": "/topic/InvoiceStatementUpdates",
                "data":
                {
                    "event":
                    {
                      "type": "updated",
                      "createdDate": "2011-11-03T15:59:06.000+0000"
                    },
                    "sobject":
                    {
                      "Name": "INV-0001",
                      "Id": "a00D0000008o6y8IAA",
                      "Status__c": "Open"
                    }
                }
            }
        }
    ]

If the JSONPath expression evaluated on the transformed message produces a
non-empty result then the `route`_ property of the rule will be used to
forward the message.

For evaluating `JSONPath <jsonpath_>`_ expressions the dialect supported by
`jsonpath-rw`_ is used including the extensions provided by `jsonpath-rw-ext`_.

route
^^^^^

The value of the `route`_ property will be used to forward the given message
if the rule's `condition`_ property produces a non-empty match. The `route`_
property should contain the same type of properties as `default_route`_.

.. include:: global.rst
