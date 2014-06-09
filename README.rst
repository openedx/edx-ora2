.. image:: https://travis-ci.org/edx/edx-ora2.png?branch=master
    :alt: Travis build status


.. image:: https://coveralls.io/repos/edx/edx-ora2/badge.png?branch=master
    :target: https://coveralls.io/r/edx/edx-ora2?branch=master
    :alt: Coverage badge


`User documentation available on ReadTheDocs`__.

__ http://edx.readthedocs.org/projects/edx-open-response-assessments


This is an initial prototype for redesigning Peer Grading and general Open Ended
Submission Evaluation. This project is in the early stages of development and is
not ready for general use.


Installation
============

The intent of this project is to be installed as Django apps that will be
included in `edx-platform <https://github.com/edx/edx-platform>`_.

For JavaScript minification and unit tests, you must `install NodeJS <http://nodejs.org/>`_.

To install dependencies and start the development ("workbench") server:

.. code:: bash

    ./scripts/workbench.sh

By default, the XBlock JavaScript will be combined and minified.  To
preserve indentation and line breaks in JavaScript source files:

.. code:: bash

    DEBUG_JS=1 ./scripts/workbench.sh

Additional arguments are passed to ``runserver``.  For example,
to start the server on port 8001:

.. code:: bash

    ./scripts/workbench.sh 8001


Celery Workers
==============

Some of the OpenAssessment APIs execute tasks asynchronously using `celery <http://docs.celeryproject.org>`_.
The tasks are executed by worker processes.

First, you will need to `install RabbitMQ <http://http://www.rabbitmq.com/download.html>`_.

Once RabbitMQ is installed, you can start a worker process locally:

.. code:: bash

    ./scripts/celery-worker.sh



Running Tests
=============

To run the Python and Javascript unit test suites:

.. code:: bash

    ./scripts/test.sh

To limit Python tests to a particular Django app:

.. code:: bash

    ./scripts/test-python.sh openassessment.xblock

To run just the JavaScript tests:

.. code:: bash

    ./scripts/test-js.sh

To run the JavaScript tests in Chrome so you can use the debugger:

.. code:: bash

    ./scripts/js-debugger.sh


Quality Check
=============

Install pylint:

.. code:: bash

    pip install pylint==0.28.0

Check for quality violations:

.. code:: bash

    pylint apps

Disable quality violations on a line or file:

.. code:: python

    # pylint: disable=W0123,E4567


<<<<<<< HEAD
Vagrant
=======

This repository includes a Vagrant configuration file, which is useful for testing
ORA2 in an environment that is closer to production:

* Uses `gunicorn <http://gunicorn.org/>`_ to serve the workbench application.
  Unlike Django ``runserver``, gunicorn will process requests in parallel.

* Uses `mysql <http://www.mysql.com/>`_ as the database, which (unlike
  `sqlite <http://www.sqlite.org/>`_) allows for simultaneous writes.

* Serves static files using `nginx <http://wiki.nginx.org/Main>`_ instead
  of Django `staticfiles <https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/>`_.

* Runs multiple `celery workers <http://celery.readthedocs.org/en/latest/>`_.

* Uses `memcached <http://memcached.org/>`_.

* Installs `EASE <https://github.com/edx/ease>`_ for AI grading, including
  its many requirements.

To use the Vagrant VM:

1) `Install Vagrant <https://docs.vagrantup.com/v2/installation/>`_.
2) ``vagrant up`` to start and provision the Vagrant VM.
3) Visit `http://192.168.44.10 <http://192.168.44.10>`_
4) You should see the workbench index page load.

After making a change to the code in the ``edx-ora2`` directory,
you must restart the services on the Vagrant VM:

1) ``vagrant ssh`` to ssh into the Vagrant VM.
2) ``./update.sh`` to restart the services, run database migrations, and collect static assets.
3) Visit `http://192.168.44.10 <http://192.168.44.10>`_

By default, the Vagrant VM also includes a monitoring tool for Celery tasks called `Flower <https://github.com/mher/flower>`_.
To use the tool, visit: `http://192.168.44.10:5555 <http://192.168.44.10:5555>`_

The log files from the Vagrant VM are located in ``edx-ora2/logs/vagrant``, which is shared with the host machine.


i18n
====

You will need to install `getttext <http://www.gnu.org/software/gettext/>`_.

To extract strings and compile messages:

.. code:: bash

    python manage.py makemessages -l en
    python manage.py makemessages -d djangojs -l en
    python manage.py compilemessages

Generate dummy strings for testing:

.. code:: bash

    i18n_tool dummy


License
=======

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How to Contribute
=================

Due to the very early stage of development we're at, we are not accepting
contributions at this time. Large portions of the API can change with little
notice.

Reporting Security Issues
=========================

Please do not report security issues in public. Please email security@edx.org

Mailing List and IRC Channel
============================

You can discuss this code on the
`edx-code Google Group <https://groups.google.com/forum/#!forum/edx-code>`_ or
in the `edx-code` IRC channel on Freenode.
