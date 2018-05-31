from asynctest import TestCase, mock

from rabbit_force.routing import Route, RoutingCondition, MessageRouter, \
    RoutingRule
from rabbit_force.exceptions import InvalidRoutingConditionError


class TestRoute(TestCase):
    def test_create(self):
        broker_name = "broker"
        exchange_name = "exchange"
        routing_key = "key"
        properties = {}

        route = Route(
            broker_name=broker_name,
            exchange_name=exchange_name,
            routing_key=routing_key,
            properties=properties
        )

        self.assertEqual(route.broker_name, broker_name)
        self.assertEqual(route.exchange_name, exchange_name)
        self.assertEqual(route.routing_key, routing_key)
        self.assertEqual(route.properties, properties)

    def test_create_without_properties(self):
        broker_name = "broker"
        exchange_name = "exchange"
        routing_key = "key"

        route = Route(
            broker_name=broker_name,
            exchange_name=exchange_name,
            routing_key=routing_key
        )

        self.assertEqual(route.broker_name, broker_name)
        self.assertEqual(route.exchange_name, exchange_name)
        self.assertEqual(route.routing_key, routing_key)
        self.assertIsNone(route.properties)


class TestRoutingCondition(TestCase):
    @mock.patch("rabbit_force.routing.parse")
    def test_init(self, parse_func):
        expression = "$"

        condition = RoutingCondition(expression)

        self.assertEqual(condition.expression, parse_func.return_value)
        parse_func.assert_called_with(expression)

    def test_init_with_invalid_expression(self):
        expression = "%"

        with self.assertRaises(InvalidRoutingConditionError):
            RoutingCondition(expression)

    def test_init_with_invalid_expression_type(self):
        expression = 4

        with self.assertRaises(InvalidRoutingConditionError):
            RoutingCondition(expression)

    def test_is_matching(self):
        condition = RoutingCondition("$")
        condition.expression = mock.MagicMock()
        condition.expression.find.return_value = [object()]
        message = object()

        result = condition.is_matching(message)

        self.assertTrue(result)
        condition.expression.find.assert_called_with(message)

    def test_is_matching_on_empty_match(self):
        condition = RoutingCondition("$")
        condition.expression = mock.MagicMock()
        condition.expression.find.return_value = []
        message = object()

        result = condition.is_matching(message)

        self.assertFalse(result)
        condition.expression.find.assert_called_with(message)


class TestMessageRouter(TestCase):
    def test_init(self):
        default_route = object()
        rules = object()

        router = MessageRouter(default_route, rules)

        self.assertEqual(router.default_route, default_route)
        self.assertEqual(router.rules, rules)

    def test_default_init(self):
        router = MessageRouter()

        self.assertIsNone(router.default_route)
        self.assertEqual(router.rules, [])

    def test_add_rule(self):
        router = MessageRouter()
        rule = object()

        router.add_rule(rule)

        self.assertEqual(router.rules, [rule])

    def test_find_route_no_rules(self):
        default_route = object()
        router = MessageRouter(default_route)
        replay_id = 12
        message = {
            "data": {
                "event": {"replayId": replay_id}
            }
        }
        source_name = "source"

        with self.assertLogs("rabbit_force.routing", "DEBUG") as log:
            result = router.find_route(source_name, message)

        self.assertIs(result, default_route)
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.routing:No routing rule found for message "
            f"{replay_id!s} from {source_name!r}, using default route"
        ])

    def test_find_route_first_matching(self):
        condition = mock.MagicMock()
        condition.is_matching.return_value = True
        route = object()
        rule = RoutingRule(condition, route)
        router = MessageRouter(rules=[rule])
        message = object()
        source_name = object()

        result = router.find_route(source_name, message)

        self.assertIs(result, route)
        condition.is_matching.assert_called_with([{
            "org_name": source_name,
            "message": message
        }])

    def test_find_route_second_matching(self):
        condition1 = mock.MagicMock()
        condition1.is_matching.return_value = False
        route1 = object()
        rule1 = RoutingRule(condition1, route1)
        condition2 = mock.MagicMock()
        condition2.is_matching.return_value = True
        route2 = object()
        rule2 = RoutingRule(condition2, route2)
        router = MessageRouter(rules=[rule1, rule2])
        message = object()
        source_name = object()

        result = router.find_route(source_name, message)

        self.assertIs(result, route2)
        condition1.is_matching.assert_called_with([{
            "org_name": source_name,
            "message": message
        }])
        condition2.is_matching.assert_called_with([{
            "org_name": source_name,
            "message": message
        }])

    def test_find_route_none_matching(self):
        condition1 = mock.MagicMock()
        condition1.is_matching.return_value = False
        route1 = object()
        rule1 = RoutingRule(condition1, route1)
        condition2 = mock.MagicMock()
        condition2.is_matching.return_value = False
        route2 = object()
        rule2 = RoutingRule(condition2, route2)
        default_route = object()
        router = MessageRouter(default_route, [rule1, rule2])
        replay_id = 12
        message = {
            "data": {
                "event": {"replayId": replay_id}
            }
        }
        source_name = object()

        with self.assertLogs("rabbit_force.routing", "DEBUG") as log:
            result = router.find_route(source_name, message)

        self.assertIs(result, default_route)
        condition1.is_matching.assert_called_with([{
            "org_name": source_name,
            "message": message
        }])
        condition2.is_matching.assert_called_with([{
            "org_name": source_name,
            "message": message
        }])
        self.assertEqual(log.output, [
            f"DEBUG:rabbit_force.routing:No routing rule found for message "
            f"{replay_id!s} from {source_name!r}, using default route"
        ])
