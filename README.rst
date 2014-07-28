.. image:: https://travis-ci.org/edx/edx-ora2.png?branch=master
    :alt: Travis build status


.. image:: https://coveralls.io/repos/edx/edx-ora2/badge.png?branch=master
    :target: https://coveralls.io/r/edx/edx-ora2?branch=master
    :alt: Coverage badge


`User documentation available on ReadTheDocs`__.

__ http://edx.readthedocs.org/projects/edx-open-response-assessments


Installation
============

The intent of this project is to be installed as Django apps that will be
included in `edx-platform <https://github.com/edx/edx-platform>`_.

To install all dependencies (assumes Ubuntu 12.04):

.. code:: bash

    make install


Running the Development Server
==============================

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


Running Tests
=============

To run all tests:

.. code:: bash

    make test

To limit Python tests to a particular module:

.. code:: bash

    ./scripts/test-python.sh openassessment/xblock/test/test_openassessment.py

To run just the JavaScript tests:

.. code:: bash

    ./scripts/test-js.sh

To run the JavaScript tests in Chrome so you can use the debugger:

.. code:: bash

    ./scripts/js-debugger.sh


i18n
====

You will need to:

1. Install `i18n-tools <https://github.com/edx/i18n-tools>`_.
2. Configure Transifex, as described in the `docs <http://docs.transifex.com/developer/client/setup>`_.
3. Install `gettext <http://www.gnu.org/software/gettext/>`_.

To extract strings and push to Transifex

.. code:: bash

    ./scripts/i18n-push.sh

To pull strings from Transifex

.. code:: bash

    ./scripts/i18n-pull.sh


License
=======

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How to Contribute
=================

Contributions are very welcome. The easiest way is to fork this repo, and then make a pull request from your fork. The first time you make a pull request, you may be asked to sign a Contributor Agreement.

Reporting Security Issues
=========================

Please do not report security issues in public. Please email security@edx.org

Mailing List and IRC Channel
============================

You can discuss this code on the
`edx-code Google Group <https://groups.google.com/forum/#!forum/edx-code>`_ or
in the `edx-code` IRC channel on Freenode.
