from unittest import TestCase

from rabbit_force.streaming_resources import StreamingResource, \
    PushTopicResource, StreamingChannelResource


class TestStreamingResource(TestCase):
    def test_registers_subclass(self):
        type_name = "ResourceName"

        class Resource(StreamingResource, type_name=type_name):
            @property
            def channel_name(self):
                return "name"

        self.assertEqual(StreamingResource.RESOURCE_TYPES[type_name],
                         Resource)


class TestPushTopicResource(TestCase):
    def test_registers_in_superclass(self):
        self.assertEqual(StreamingResource.RESOURCE_TYPES["PushTopic"],
                         PushTopicResource)

    def test_returns_channel_name(self):
        name = "MyTopic"
        topic = PushTopicResource(name, resource_attributes=None)

        self.assertEqual(topic.channel_name, "/topic/" + name)


class TestStreamingChannelResource(TestCase):
    def test_registers_in_superclass(self):
        self.assertEqual(StreamingResource.RESOURCE_TYPES["StreamingChannel"],
                         StreamingChannelResource)

    def test_returns_channel_name(self):
        name = "MyChannel"
        topic = StreamingChannelResource(name, resource_attributes=None)

        self.assertEqual(topic.channel_name, name)
