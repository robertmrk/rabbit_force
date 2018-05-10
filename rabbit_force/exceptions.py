"""Exception types

Exception hierarchy::

    RabbitForceError
        SpecificationError
        NetworkError
        ServerError
            SalesforceError
"""


class RabbitForceError(Exception):
    """Base exception type.

    All exceptions of the package inherit from this class.
    """


class SpecificationError(RabbitForceError):
    """Invalid value or type in the config specification"""


class NetworkError(RabbitForceError):
    """Network related error"""


class ServerError(RabbitForceError):
    """Server side error"""


class SalesforceError(ServerError):
    """Salesforce error"""


class SalesforceRestError(SalesforceError):
    """Salesforce REST API error"""


class SalesforceMultipleChoicesError(SalesforceRestError):
    """When an external ID exists in more than one record"""


class SalesforceNotModifiedError(SalesforceRestError):
    """The request content has not changed since a specified date and time"""


class SalesforceBadRequestError(SalesforceRestError):
    """The request couldn’t be understood"""


class SalesforceUnauthorizedError(SalesforceRestError):
    """The _session ID or OAuth token used has expired or is invalid"""


class SalesforceForbiddenError(SalesforceRestError):
    """The request has been refused"""


class SalesforceNotFoundError(SalesforceRestError):
    """The requested resource couldn’t be found"""


class SalesforceMethodNotAllowedError(SalesforceRestError):
    """The method specified in the Request-Line isn’t allowed for the
    resource specified in the URI"""


class SalesforceUnsupportedMediaTypeError(SalesforceRestError):
    """The entity in the request is in a format that’s not supported by the
    specified method"""


class SalesforceInternalServerError(SalesforceRestError):
    """An error has occurred within Lightning Platform, so the request
    couldn’t be completed"""


class StreamingError(SalesforceError):
    """Salesforce streaming error"""


class InvalidOperation(SpecificationError):
    """An invalid operation"""
