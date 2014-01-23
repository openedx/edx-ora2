.. _api:

Public Interface
----------------

Every Django application in edx-tim has an `api.py` that is its public
interface. If you are using one of these applications from the outside, you
should only import things from that module. The ground rules for api modules
are:

1. All inputs and outputs must be trivially serializable to JSON. This means
   `None`, `int`, `float`, `unicode`, `list`, `tuple`, `dict`, `namedtuple`, and
   `datetime`.
2. Returned objects should not have methods or business logic attached to them.
3. ?

Submissions
-----------

.. automodule:: submissions.api
   :members:

Peer Assessment
---------------

.. automodule:: openassessment.peer.api
   :members:


Internals
=========

Submissions
-----------
.. automodule:: submissions.models
   :members:
