.. _api:

Public API
----------

Every Django application in edx-ora2 has an `api.py` that is its public
interface. If you are using one of these applications from the outside, you
should only import things from that module. The ground rules for api modules
are:

1. All inputs and outputs must be trivially serializable to JSON. This means
   `None`, `int`, `float`, `unicode`, `list`, `tuple`, `dict`, and `datetime`.
2. Returned objects should not have methods or business logic attached to them.
3. Caller should assume that these calls can be moderately expensive, as they
   may one day move out of process and become network calls. So calling
   something a hundred times in a loop should be avoided.

Submissions
***********

.. automodule:: submissions.api
   :members:

Peer Assessment
***************

.. automodule:: openassessment.assessment.api.peer
   :members:

Self Assessment
***************

.. automodule:: openassessment.assessment.api.self
   :members:

Example-Based Assessment (AI)
*****************************

.. automodule:: openassessment.assessment.api.ai
   :members:

Student Training
****************

.. automodule:: openassessment.assessment.api.student_training
   :members:

Workflow Assessment
*******************

.. automodule:: openassessment.workflow
   :members:


Django Apps
-----------

Submissions
***********

The Submissions app is responsible for:

1. Storing and retrieving student submissions for answering a given problem.
2. Storing and retriveing the raw scores assigned to those submissions.
3. Retrieving the raw scores for all items associated with a particular student
   in a particular course.

This application is ignorant of the content of submissions, and assumes them to
simply be opaque unicode strings.


Models
++++++
.. automodule:: submissions.models
   :members:


Assessment
**********

Models
++++++
.. automodule:: openassessment.assessment.models.base
   :members:

.. automodule:: openassessment.assessment.models.peer
   :members:

.. automodule:: openassessment.assessment.models.peer
   :members:

.. automodule:: openassessment.assessment.models.training
   :members:

.. automodule:: openassessment.assessment.models.student_training
   :members:



Workflow
********

Models
++++++
.. automodule:: openassessment.workflow.models
   :members:

