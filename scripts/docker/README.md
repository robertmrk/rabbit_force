# rabbit_force

[rabbit_force](https://github.com/robertmrk/rabbit_force) is a [Salesforce Streaming API](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm) to [RabbitMQ](http://www.rabbitmq.com/)
adapter service. It listens for event messages from
[Salesforce's Streaming API](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm) and forwards them to a
[RabbitMQ broker](http://www.rabbitmq.com/) for you, so you don't have to.

[Streaming API](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm) is useful when you want notifications to be pushed from
the server to the client based on criteria that you define with
[PushTopics](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/working_with_pushtopics.htm) or to receive
[generic streaming](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/generic_streaming_intro.htm#generic_streaming_intro) messages. While
[RabbitMQ](http://www.rabbitmq.com/) is one of the most popular options for implementing
inter-service communication in a [microservice architecture](http://microservices.io/patterns/communication-style/messaging.html).

While there are lots of great client implementations for RabbitMQ/AMQP for
various languages, there are a lot less Streaming API clients, and many of them
are badly maintained. Furthermore RabbitMQ offers much more flexible message
consumption techniques.

rabbit_force aims to fix these problems, by providing and adapter between the
Streaming API and RabbitMQ, so inter-connected services can consume Streaming
API event messages with RabbitMQ. It even supports connection with multiple
Salesforce orgs, multiple RabbitMQ brokers, and routing messages between them.

## Features

- Forward [Streaming API](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm) messages from one or more Salesforce orgs to
  one or more [RabbitMQ brokers](http://www.rabbitmq.com/)
- Route incoming messages to a specific broker and exchange with the
  specified routing key and properties, with the help of routing rules defined
  as [JSONPath](http://goessner.net/articles/JsonPath/) expressions
- Support for Salesforce's replay extension for [message reliability and
  durability](https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/using_streaming_api_durability.htm) by storing replay markers in a [Redis](https://redis.io/)
  database
- Configurable error handling behavior, either fail instantly or try to recover
  from network and service outages
- Message sources, sinks and routing configurable with JSON or YAML
  configuration files
- Implemented using [python asyncio](https://docs.python.org/3/library/asyncio.html) for efficient handling of IO intensive operations

## How to use this image
The image accepts the same [command line arguments](https://rabbit-force.readthedocs.io/en/latest/command_line.html#usage) as the standalone application. The only mandatory argument is the path to the configuration file. 

### Start a rabbit_force instance

If the configuration file is located on the host, then you should bind mount its directory into the container and you should specify its path inside the container as a positional argument.
```bash
$ docker run -d --name rabbit_force -v /path/to/config:/config:ro robertmrk/rabbit_force:latest /config/config.yaml
```

### Use an embedded configuration file

Alternatively, a simple `Dockerfile` can be used to generate a new image that includes the necessary configuration.
```
FROM robertmrk/rabbit_force:latest

COPY config.yaml ./

CMD ["config.yaml"]
```

```bash
$ docker run -d --name rabbit_force configured-rabbit_force
```

## Configuration

To customize the behavior of the application for your use case check out the [configuration file reference](https://rabbit-force.readthedocs.io/en/latest/configuration.html) and the [configuration examples](https://rabbit-force.readthedocs.io/en/latest/examples.html) in the [documentation](https://rabbit-force.readthedocs.io/en/latest/index.html).

## License

rabbit_force source code is available under the [MIT License](https://opensource.org/licenses/MIT).