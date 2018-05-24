"""Message routing classes"""
from collections import namedtuple

from jsonpath_ng.ext import parse
from jsonpath_ng.lexer import JsonPathLexerError

from rabbit_force.exceptions import InvalidRoutingConditionError


class Route(namedtuple("Route", ("broker_name", "exchange_name", "routing_key",
                                 "properties"))):
    """Class for storing routing parameters"""
    __slots__ = ()

    def __new__(cls, broker_name, exchange_name, routing_key, properties=None):
        """Create a new instance

        :param str broker_name: The name of the sink that should consume the \
        message
        :param str exchange_name: The name of the exchange which should \
        receive the message
        :param str routing_key: The message's routing key parameter
        :param dict properties: Additional message properties
        :return: A new instance
        :rtype: Route
        """
        return super().__new__(cls, broker_name, exchange_name, routing_key,
                               properties)


class RoutingCondition:  # pylint: disable=too-few-public-methods
    """Evaluates a JSONPath expression on a message"""

    def __init__(self, jsonpath_expression):
        """
        :param str jsonpath_expression: JSONPath expression
        """
        try:
            self.expression = parse(jsonpath_expression)
        except (JsonPathLexerError, TypeError) as error:
            raise InvalidRoutingConditionError(str(error)) from error

    def is_matching(self, message):
        """Evaluate the JSONPath expression on the *message*

        :param dict message: A message
        :return: True if there is at least a single match returned otherwise \
        False
        :rtype: bool
        """
        result = self.expression.find(message)
        return bool(result)


#: Message routing rule
RoutingRule = namedtuple("RoutingRule", ["condition", "route"])


class MessageRouter:
    """Finds the correct route for messages based on routing rules"""

    def __init__(self, default_route=None, rules=None):
        """
        :param default_route: A default route to use if none of the \
        routing rules match the given message
        :type default_route: Route or None
        :param rules: A list of routing rules
        :type rules: list[RoutingRule] or None
        """
        self.default_route = default_route
        self.rules = rules or []

    def add_rule(self, rule):
        """Add a routing rule to the list of rules

        :param RoutingRule rule: A routing rule
        """
        self.rules.append(rule)

    def find_route(self, source_name, message):
        """Find the correct route for the given *source_name* and *message*

        :param str source_name: The name of the message's source
        :param dict message: A message
        :return: The routing parameters associated with the first routing \
        rule that matches the *source_name* and *message*, or the default \
        route if none of the rules produce a positive match
        """
        # create a message that contains the source name and the message
        # embed the message in a list, so array filtering instructions can be
        # used to check for matching messages in RoutingCondition
        message = [
            {
                "org_name": source_name,
                "message": message
            }
        ]

        # by default return the default route
        route = self.default_route

        # find the first matching routing rule and use its routing parameters
        try:
            matching_rule = next(rule for rule in self.rules
                                 if rule.condition.is_matching(message))
            route = matching_rule.route

        # don't change current value of route if no rule produces a positive
        # match
        except StopIteration:
            pass

        return route
