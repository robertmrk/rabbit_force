User's guide
============

Installation
------------

Command line reference
----------------------

Usage
~~~~~
::

    $ python -m rabbit_force [OPTIONS] CONFIG_FILE


Message sources, sinks and message routing rules should be defined in a
``CONFIG_FILE`` either in JSON (.json) or in YAML (.yaml, .yml) format.
For a detailed explanation about the format of the configuration file check the
:ref:`configuration reference <config>`.

Options
~~~~~~~

* **--ignore-replay-storage-errors** - Ignore errors that might occur on
  reading or writing replay marker values.
* **--ignore-sink-errors** - Ignore errors that might occur if a message can't
  be forwarded to a given message sink due to network or configuration errors.
* **--source-connection-timeout** - If the connection to the Streaming API
  fails due to network errors or service outages, try to reconnect for
  the given amount of seconds before producing an error.
  If ``0`` timeout is specified, then the service will try to
  re-establish the connection indefinitely.
* **-v**, **--verbosity** - Logging detail level (1-3).
* **-t**, **--show-trace** - Show full backtrace on error.
* **--version** - Show the version and exit.
* **--help** - Show help message and exit.

.. _config:

Configuration
-------------

Examples
--------
