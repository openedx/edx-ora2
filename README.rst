Open Response Assessment |build-status| |coverage-status|
=========================================================

`User docs <http://edx.readthedocs.org/projects/edx-partner-course-staff/en/latest/exercises_tools/open_response_assessments/index.html>`_


Installation
============

The intent of this project is to be installed as Django apps that will be included in `edx-platform <https://github.com/edx/edx-platform>`_.

But development is done in the Workbench which is part of the `xblock-sdk <https://github.com/edx/xblock-sdk>`_. Currently Ubuntu 12.04 is assumed. You can setup everything in a Vagrant instance.

To do so install the latest VirtualBox >= 4.3.12 and the latest Vagrant >= 1.6.5.

Clone the repo:

.. code:: bash

    mkdir orastack
    cd orastack
    git clone git@github.com:edx/edx-ora2.git

Create the Vagrant instance:

.. code:: bash

    ln -s ./edx-ora2/Vagrantfile ./
    vagrant plugin install vagrant-vbguest
    vagrant up

The first vagrant up will fail when setting up shared folders (because the user ora2 does not exist) so do:

.. code:: bash

    vagrant provision
    vagrant reload

Now you can ssh into the vagrant machine:

.. code:: bash

    vagrant ssh
    sudo su ora2

To install all dependencies:

.. code:: bash

    make install-sys-requirements
    make install
    make install-dev


Running the Development Server
==============================

.. code:: bash

    ./scripts/workbench.sh

Additional arguments are passed to ``runserver``.  For example,
to start the server on port 9000:

.. code:: bash

    ./scripts/workbench.sh 0.0.0.0:9000


Combining and Minifying JavaScript and Sass
============================================

To reduce page size, the OpenAssessment XBlock serves combined/minified
versions of JavaScript and CSS.  This combined/minified files are checked
into the git repository.

If you modify JavaScript or Sass, you MUST regenerate the combined/minified
files:

.. code:: bash

    # Combine/minify JavaScript
    make javascript

    # Combine/minify CSS (from Sass)
    make sass

Make sure you commit the combined/minified files to the git repository!


Running Tests
=============

To run all unit tests:

.. code:: bash

    make test

To limit Python tests to a particular module:

.. code:: bash

    ./scripts/test-python.sh openassessment/xblock/test/test_openassessment.py

To run just the JavaScript tests:

.. code:: bash

    make test-js

To run the JavaScript tests in Chrome so you can use the debugger:

.. code:: bash

    make test-js-debug

There are also acceptance and accessibility tests that run can be run against a sandbox.  For more information, about how to run these from your machine, check out `test/acceptance/README.rst <https://github.com/edx/edx-ora2/blob/master/test/acceptance/README.rst/>`__.


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

.. |build-status| image:: https://travis-ci.org/edx/edx-ora2.png?branch=master
   :target: https://travis-ci.org/edx/edx-ora2
   :alt: Travis build status
.. |coverage-status| image:: https://coveralls.io/repos/edx/edx-ora2/badge.png?branch=master
   :target: https://coveralls.io/r/edx/edx-ora2?branch=master
   :alt: Coverage badge
