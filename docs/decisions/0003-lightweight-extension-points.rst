Lightweight extension points
############################

Status
******

**Draft** *2024-02-27*

Context
*******

Open Responses are commonly used in education for assessment purposes and the flexibility of ORA has made it a key feature of the Open edX platform. However, as developers, it is tough to accommodate the needs of educators and other stakeholders in the teaching process when they want to enhance the learner's experience with other tools such as plagiarism detection, AI grading, coding graders, and others.

As the code is open, it is always possible to modify it. Still, it might result in a technical maintenance debt, which usually prevents educators from experimenting or installations from upgrading to newer versions once the changes to ORA become important in the teaching process.

Decisions
*********

As the first step towards making the instructor's involvement in the learners' lifecycle more flexible, we will introduce two extension points in the ORA codebase. These extension points will be built on top of the `Hooks Extensions Framework`_. The definitions for these extension points will reside in `openedx-filters`_ and `openedx-events`_. These definitions will be imported into the edx-ora2 repository and triggered in two places during the learners' lifecycle, resulting in minimal modifications to the ORA implementation.

The first extension point we will implement is an `Open edX Filter`_ that will be executed before `rendering the submission HTML section of the block for the legacy view`_, with input arguments ``context`` and ``template path``. This implementation will allow us to modify what's rendered to the student, via the view ``context`` and ``template``, for cases when needed. 

The second extension point to be implemented is an `Open edX Event`_. It will be sent `after a student submits a response to the assessment`_ with the student's submission key data, like the ORA submission ID and files uploaded in the submission, as the event's payload. This event will allow us to take action after a submission is made based on the data sent.

Consequences
************

Extension developers often use those extension points in Open edX plugins to enhance the functionality of an existing application. When installing edx-ora2, developers can implement more use cases out-of-the-box by configuring it with plugins that use these extension points. These use cases include modify the context passed to ``legacy/response/oa_response.html`` , changing the template that is rendered to the student, and sending students' submission data to another service.

For instance, if a developer wants to add an acknowledgment notice to the submission template, they can implement a `pipeline step`_ for the filter that modifies the ``oa_response.html`` template for an ``oa_response_ack_modified.html`` template with its custom context. See `how to implement pipeline steps`_ for more information. To act on the submission-created notification, the developer can listen to the Open edX event since the event payload has enough information to get the student's submissions, including files, enabling the event receiver to obtain and send the submission to another service for analysis. See `how to listen for Open edX Events`_ for more information. 

These changes allow extension developers to interact with a crucial part of the student's assessment lifecycle. However, when none of these extension points are configured, ORA assessments will behave as usual. This first step sets a precedent for ORA developers to implement more extension points during the ORA users' lifecycle, enabling additional use cases to be built on top of them.

Rejected Alternatives
*********************

Given that there is currently no other option for extending ORA without a fork, we are not rejecting any other alternative. It could be argued that we are rejecting the construction of a more extensive (or more comprehensive) framework for extension, but it's more like this is the first step towards a larger framework. If we were to propose a project to extend ORA with a mechanism for dependency injection, we would still propose it to be built on top of the hooks framework.

At this ADR, we are only committing to the first few hooks because we understand very well the effort it requires. However, there is no technical limit for this proposal to grow into more hooks and eventually support a broad array of extension use cases.

.. _Hooks Extensions Framework: https://open-edx-proposals.readthedocs.io/en/latest/architectural-decisions/oep-0050-hooks-extension-framework.html
.. _rendering the submission HTML section of the block for the legacy view: https://github.com/openedx/edx-ora2/blob/master/openassessment/xblock/ui_mixins/legacy/views/submission.py#L19
.. _Open edX Filter: https://docs.openedx.org/projects/openedx-filters/en/latest/
.. _Open edX Event: https://docs.openedx.org/projects/openedx-filters/en/latest/
.. _pipeline step: https://docs.openedx.org/projects/openedx-filters/en/latest/concepts/glossary.html#pipeline-steps
.. _how to implement pipeline steps: https://docs.openedx.org/projects/openedx-filters/en/latest/how-tos/using-filters.html#implement-pipeline-steps
.. _how to listen for Open edX Events: https://docs.openedx.org/projects/openedx-events/en/latest/how-tos/using-events.html#receiving-events
.. _after a student submits a response to the assessment: https://github.com/openedx/edx-ora2/blob/master/openassessment/xblock/ui_mixins/legacy/handlers_mixin.py#L67
.. _platform roadmap GH ticket: https://github.com/openedx/platform-roadmap/issues/253
.. _openedx-events: https://github.com/openedx/openedx-events
.. _openedx-filters: https://github.com/openedx/openedx-filters
