.. image:: https://travis-ci.org/edx/edx-tim.png?branch=master
    :alt: Travis build status

This is an initial prototype for redesigning Peer Grading and general Open Ended
Submission Evaluation. This project is in the early stages of development and is
not ready for general use.

Installation
============

The intent of this project is to be installed as Django apps that will be
included in `edx-platform <https://github.com/edx/edx-platform>`_. To install
for development purposes, run::

  pip install -r requirements/dev.txt
  pip install -e .

The second line is necessary to register edx-tim's XBlock so that it will show
up in the XBlock workbench.

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
