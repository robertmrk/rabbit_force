Changelog
=========

0.1.0
-----

- Forward `Streaming API <api_>`_ messages from one or more Salesforce orgs to
  one or more `RabbitMQ brokers <rabbitmq_>`_
- Route incoming messages to a specific broker and exchange with the
  specified routing key and properties, with the help of routing rules defined
  as `JSONPath <jsonpath_>`_ expressions
- Support for Salesforce's replay extension for `message reliability and
  durability <replay_>`_ by storing replay markers in a `Redis <redis_>`_
  database
- Configurable error handling behavior, either fail instantly or try to recover
  from network and service outages
- Message sources, sinks and routing configurable with JSON or YAML
  configuration files
- Implemented using `python asyncio <asyncio_>`_ for efficient handling of
  IO intensive operations

.. _aiohttp: https://github.com/aio-libs/aiohttp/
.. _aiocometd: https://github.com/robertmrk/aiocometd/
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _api: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm
.. _PushTopic: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/working_with_pushtopics.htm
.. _GenericStreaming: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/generic_streaming_intro.htm#generic_streaming_intro
.. _replay: https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/using_streaming_api_durability.htm
.. _CometD: https://cometd.org/
.. _Comet: https://en.wikipedia.org/wiki/Comet_(programming)
.. _Bayeux: https://docs.cometd.org/current/reference/#_bayeux
.. _ext: https://docs.cometd.org/current/reference/#_bayeux_ext
.. _password_auth: https://help.salesforce.com/articleView?id=remoteaccess_oauth_username_password_flow.htm&type=5
.. _refresh_auth: https://help.salesforce.com/articleView?id=remoteaccess_oauth_refresh_token_flow.htm&type=5
.. _connected_app: https://help.salesforce.com/articleView?id=connected_app_overview.htm&type=5
.. _sf_auth: https://help.salesforce.com/articleView?id=remoteaccess_authenticate_overview.htm
.. _web_server_auth: https://help.salesforce.com/articleView?id=remoteaccess_oauth_web_server_flow.htm&type=5
.. _rabbitmq: http://www.rabbitmq.com/
.. _microservice: http://microservices.io/patterns/communication-style/messaging.html
.. _jsonpath: http://goessner.net/articles/JsonPath/
.. _redis: https://redis.io/
