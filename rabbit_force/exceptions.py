"""Exception types

Exception hierarchy::

    RabbitForceError
        RabbitForceValueError
        NetworkError
        ServerError
            SalesforceError
"""


class RabbitForceError(Exception):
    """Base exception type.

    All exceptions of the package inherit from this class.
    """


class RabbitForceValueError(RabbitForceError):
    """Inappropriate argument value"""


class NetworkError(RabbitForceError):
    """Network related error"""


class ServerError(RabbitForceError):
    """Server side error"""


class SalesforceError(ServerError):
    """Salesforce error"""
