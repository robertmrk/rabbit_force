from unittest import TestCase, mock
import logging

from click.testing import CliRunner

from rabbit_force.__main__ import configure_logger, LoggingParameters, \
    Verbosity, main


class TestConfiureLogger(TestCase):
    @mock.patch("rabbit_force.__main__.logging")
    def test_configure_logger(self, logging_mock):
        parameters = LoggingParameters(
            level=logging.INFO,
            name=None,
            format="fmt"
        )
        verbosity = Verbosity.APP_INFO
        logger = mock.MagicMock()
        logging_mock.getLogger.return_value = logger
        handler = mock.MagicMock()
        logging_mock.StreamHandler.return_value = handler
        formatter = mock.MagicMock()
        logging_mock.Formatter.return_value = formatter
        in_dict = "rabbit_force.__main__.VERBOSITY_LOGGING_PARAMETERS"

        with mock.patch.dict(in_dict, {verbosity: parameters}):
            result = configure_logger(verbosity)

        self.assertEqual(result, logger)
        logger.setLevel.assert_called_with(parameters.level)
        logging_mock.StreamHandler.assert_called_with()
        handler.setLevel.assert_called_with(parameters.level)
        logging_mock.Formatter.assert_called_with(parameters.format)
        handler.setFormatter.assert_called_with(formatter)
        logger.addHandler.asssert_called_with(handler)

    @mock.patch("rabbit_force.__main__.logging")
    def test_configure_logger_sets_default_logger_for_aioamqp(self,
                                                              logging_mock):
        parameters = LoggingParameters(
            level=logging.INFO,
            name="name",
            format="fmt"
        )
        verbosity = Verbosity.APP_INFO
        logger = mock.MagicMock()
        aioamqp_logger = mock.MagicMock()
        logging_mock.getLogger.side_effect = (logger, aioamqp_logger)
        handler = mock.MagicMock()
        logging_mock.StreamHandler.return_value = handler
        formatter = mock.MagicMock()
        logging_mock.Formatter.return_value = formatter
        in_dict = "rabbit_force.__main__.VERBOSITY_LOGGING_PARAMETERS"
        null_handler = mock.MagicMock()
        logging_mock.NullHandler.return_value = null_handler

        with mock.patch.dict(in_dict, {verbosity: parameters}):
            result = configure_logger(verbosity)

        self.assertEqual(result, logger)
        logger.setLevel.assert_called_with(parameters.level)
        logging_mock.StreamHandler.assert_called_with()
        handler.setLevel.assert_called_with(parameters.level)
        logging_mock.Formatter.assert_called_with(parameters.format)
        handler.setFormatter.assert_called_with(formatter)
        logger.addHandler.asssert_called_with(handler)
        logging_mock.getLogger.assert_has_calls([
            mock.call(parameters.name), mock.call("aioamqp")
        ])
        aioamqp_logger.addHandler.assert_called_with(null_handler)


class TestMain(TestCase):
    @mock.patch("rabbit_force.__main__.Application")
    @mock.patch("rabbit_force.__main__.load_config")
    @mock.patch("rabbit_force.__main__.configure_logger")
    def test_main(self, configure_logger_func, load_config_func, app_cls):
        config_file = "config.json"
        source_connection_timeout = 20
        verbosity = 2
        logger = mock.MagicMock()
        configure_logger_func.return_value = logger
        config = object()
        load_config_func.return_value = config
        app = mock.MagicMock()
        app_cls.return_value = app

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open(config_file, "w"):
                pass
            result = runner.invoke(main, [config_file,
                                          "--ignore-replay-storage-errors",
                                          "--ignore-sink-errors",
                                          "--source-connection-timeout",
                                          str(source_connection_timeout),
                                          "--verbosity",
                                          str(verbosity),
                                          "--show-trace"])

        self.assertEqual(result.exit_code, 0)
        configure_logger_func.assert_called_with(verbosity)
        load_config_func.assert_called_with(config_file)
        app_cls.assert_called_with(
            config,
            ignore_replay_storage_errors=True,
            ignore_sink_errors=True,
            source_connection_timeout=source_connection_timeout
        )
        app.run.assert_called()
        self.assertEqual(logger.info.call_args_list, [
            mock.call("Starting up ..."),
            mock.call("Configuration loaded from %r", config_file)
        ])
        self.assertEqual(logger.debug.call_args_list, [
            mock.call("Creating application"),
            mock.call("Starting application")
        ])

    @mock.patch("rabbit_force.__main__.Application")
    @mock.patch("rabbit_force.__main__.load_config")
    @mock.patch("rabbit_force.__main__.configure_logger")
    def test_main_on_error(self, configure_logger_func, load_config_func,
                           app_cls):
        config_file = "config.json"
        source_connection_timeout = 20
        verbosity = 2
        logger = mock.MagicMock()
        configure_logger_func.return_value = logger
        config = object()
        load_config_func.return_value = config
        app = mock.MagicMock()
        app_cls.return_value = app
        error = Exception("message")
        app.run.side_effect = error

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open(config_file, "w"):
                pass
            result = runner.invoke(main, [config_file,
                                          "--ignore-replay-storage-errors",
                                          "--ignore-sink-errors",
                                          "--source-connection-timeout",
                                          str(source_connection_timeout),
                                          "--verbosity",
                                          str(verbosity),
                                          "--show-trace"])

        self.assertEqual(result.exit_code, 1)
        configure_logger_func.assert_called_with(verbosity)
        load_config_func.assert_called_with(config_file)
        app_cls.assert_called_with(
            config,
            ignore_replay_storage_errors=True,
            ignore_sink_errors=True,
            source_connection_timeout=source_connection_timeout
        )
        app.run.assert_called()
        self.assertEqual(logger.info.call_args_list, [
            mock.call("Starting up ..."),
            mock.call("Configuration loaded from %r", config_file)
        ])
        self.assertEqual(logger.debug.call_args_list, [
            mock.call("Creating application"),
            mock.call("Starting application")
        ])
        logger.error.assert_called_with(f"Unexpected error: \n%r", error,
                                        exc_info=True)
