"""rabbit_force application entrypoint"""
import logging
from enum import IntEnum
from collections import namedtuple

import click

from .config import load_config
from .app import Application
from ._metadata import TITLE, VERSION


class Verbosity(IntEnum):
    """Logging detail level"""
    #: Application messages with ``info`` level and above
    APP_INFO = 1
    #: Application messages with ``debug`` level and above
    APP_DEBUG = 2
    #: Application and library messages with ``debug`` level and above
    APP_AND_LIBRARY_DEBUG = 3


#: Basic logging parameters
LoggingParameters = namedtuple("LoggingParameters",
                               ("level", "name", "format"))
LoggingParameters.level.__doc__ = "The level of the logger and handler"
LoggingParameters.name.__doc__ = "Name of the application's logger"
LoggingParameters.format.__doc__ = "Format definition for the log formatter"

#: Verbosity specific logging parameters
VERBOSITY_LOGGING_PARAMETERS = {
    Verbosity.APP_INFO: LoggingParameters(
        level=logging.INFO,
        name=__package__,
        format="%(asctime)s:%(levelname)s: %(message)s"
    ),
    Verbosity.APP_DEBUG: LoggingParameters(
        level=logging.DEBUG,
        name=__package__,
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
    ),
    Verbosity.APP_AND_LIBRARY_DEBUG: LoggingParameters(
        level=logging.DEBUG,
        name=None,
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
    )
}


def configure_logger(verbosity):
    """Configure the application's logger

    :param Verbosity verbosity: Logging verbosity
    :return: Application's root logger
    :rtype: logging.Logger
    """
    logging_parameters = VERBOSITY_LOGGING_PARAMETERS[verbosity]

    # create logger and set level
    logger = logging.getLogger(logging_parameters.name)
    logger.setLevel(logging_parameters.level)

    # create console handler and set level
    handler = logging.StreamHandler()
    handler.setLevel(logging_parameters.level)

    # create formatter
    formatter = logging.Formatter(logging_parameters.format)

    # add formatter to handler
    handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(handler)

    # if we're not using the root logger then set a null handler for the
    # aioamqp library (because it doesn't has one configured by default)
    if logging_parameters.name:
        logging.getLogger("aioamqp").addHandler(logging.NullHandler())

    return logger


# pylint: disable=too-many-arguments
@click.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--ignore-replay-storage-errors", default=False, is_flag=True,
              help="Ignore errors that might occur on reading or writing "
                   "replay marker values.")
@click.option("--ignore-sink-errors", default=False, is_flag=True,
              help="Ignore errors that might occur if a message can't be "
                   "forwarded to a given message sink due to network or "
                   "configuration errors.")
@click.option("--source-connection-timeout", type=click.IntRange(min=0),
              default=10, show_default=True,
              help="If the connection to the Streaming API fails due to "
                   "network errors or service outages, try to reconnect for "
                   "the given amount of seconds before producing an error. "
                   "If 0 timeout is specified, then the service will try to "
                   "re-establish the connection indefinitely.")
@click.option("-v", "--verbosity", type=click.IntRange(min=1, max=3),
              default=1, show_default=True, help="Logging detail level (1-3).")
@click.option("-t", "--show-trace", default=False, is_flag=True,
              help="Show full backtrace on error.")
@click.version_option(VERSION)
def main(config_file, ignore_replay_storage_errors, ignore_sink_errors,
         source_connection_timeout, verbosity, show_trace):
    """rabbit_force is a Salesforce Streaming API to RabbitMQ adapter service.
    It listens for event messages from Salesforce's Streaming API and forwards
    them to a RabbitMQ broker for you, so you don't have to.

    Message sources, sinks and message routing rules should be defined in a
    CONFIG_FILE either in JSON (.json) or in YAML (.yaml, .yml) format.
    """
    logger = configure_logger(verbosity)
    logger.info("Starting up ...")

    try:
        file_path = config_file
        config = load_config(file_path)

        logger.info("Configuration loaded from %r", file_path)

        logger.debug("Creating application")
        app = Application(
            config,
            ignore_replay_storage_errors=ignore_replay_storage_errors,
            ignore_sink_errors=ignore_sink_errors,
            source_connection_timeout=source_connection_timeout
        )

        logger.debug("Starting application")
        app.run()

    except Exception as error:  # pylint: disable=broad-except
        logger.error(f"Unexpected error: \n%r", error, exc_info=show_trace)
        exit(1)


# pylint: enable=too-many-arguments

if __name__ == "__main__":   # pragma: no cover
    # pylint: disable=no-value-for-parameter,unexpected-keyword-arg
    main(prog_name=f"python -m {TITLE}")
    # pylint: enable=no-value-for-parameter,unexpected-keyword-arg
