Open Response Assessment |build-status| |coverage-status|
=========================================================

`User docs <http://edx.readthedocs.org/projects/edx-partner-course-staff/en/latest/exercises_tools/open_response_assessments/index.html>`_


Installation, Tests, and other Developer Tasks
==============================================

edX engineers follow the `guides on our wiki <https://openedx.atlassian.net/wiki/spaces/EDUCATOR/pages/9765004/ORA+Developer+Guide>`_.
Reading this page before contributing is highly recommended.

License
=======

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How to Contribute
=================

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork. The first time you make a pull request, you
may be asked to sign a Contributor Agreement.

Before committing any changes, remember to regenerate the CSS and the bundled
JavaScript files. Your changes may work locally because Studio, LMS and the
tests access the raw files directly, but on a sandbox or production-like
environment only the bundled files are used. You should do the following:

.. code:: bash

    make javascript sass

**Note**: This can be automated by installing git hooks using:

.. code:: bash

    make install-git-hooks

Reporting Security Issues
=========================

Please do not report security issues in public. Please email security@edx.org

Mailing List and Slack
======================

You can get help with this code on our `mailing lists`_ or in real-time
conversations on `Slack`_.

.. _mailing lists: https://open.edx.org/getting-help
.. _Slack: https://open.edx.org/getting-help

.. |build-status| image:: https://travis-ci.org/edx/edx-ora2.png?branch=master
   :target: https://travis-ci.org/edx/edx-ora2
   :alt: Travis build status
.. |coverage-status| image:: https://coveralls.io/repos/edx/edx-ora2/badge.png?branch=master
   :target: https://coveralls.io/r/edx/edx-ora2?branch=master
   :alt: Coverage badge
