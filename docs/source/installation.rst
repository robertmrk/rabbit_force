Installation
============

Get rabbit_force by downloading the `latest release <rabbit_force_releases_>`_,
or clone it from `github <rabbit_force_github_>`_::

    $ git clone https://github.com/robertmrk/rabbit_force.git

rabbit_force requires python 3.7 and `pipenv`_ to be installed.

To install pipenv run::

    $ pip install pipenv

To install rabbit_force and all of its dependencies in a virtual environment
run::

    $ pipenv install --ignore-pipfile

then activate the virtual environment::

    $ pipenv shell

.. include:: global.rst

Docker
------

The `public docker image <https://hub.docker.com/r/robertmrk/rabbit_force>`_ can
be found on docker hub.

.. code-block:: bash

    $ docker pull robertmrk/rabbit_force

Start a rabbit_force instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the configuration file is located on the host, then you should bind mount its
directory into the container and you should specify its path inside the
container as a positional argument.

.. code-block:: bash

    $ docker run -d --name rabbit_force -v /path/to/config:/config:ro
    robertmrk/rabbit_force:latest /config/config.yaml

Use an embedded configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Alternatively, a simple ``Dockerfile`` can be used to generate a new image that
includes the necessary configuration.

.. code-block::

    FROM robertmrk/rabbit_force:latest

    COPY config.yaml ./

    CMD ["config.yaml"]


.. code-block:: bash

    $ docker run -d --name rabbit_force configured-rabbit_force