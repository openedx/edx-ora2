.. image:: https://travis-ci.org/edx/edx-tim.png?branch=master
    :alt: Travis build status


.. image:: https://coveralls.io/repos/edx/edx-tim/badge.png?branch=master
    :target: https://coveralls.io/r/edx/edx-tim?branch=master
    :alt: Coverage badge


This is an initial prototype for redesigning Peer Grading and general Open Ended
Submission Evaluation. This project is in the early stages of development and is
not ready for general use.


Installation
============

The intent of this project is to be installed as Django apps that will be
included in `edx-platform <https://github.com/edx/edx-platform>`_.

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


Running Tests
=============

To run the Python and Javascript unit test suites:

.. code:: bash

    ./scripts/test.sh


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
