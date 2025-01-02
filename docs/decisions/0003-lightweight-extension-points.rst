Lightweight extension points
############################

Status
******

**Accepted** *2024-04-04*

Context
*******

Open Responses are commonly used in education for assessment purposes and the flexibility of ORA has made it a key feature of the Open edX platform. However, as developers, it is tough to accommodate the needs of educators and other stakeholders in the teaching process when they want to enhance the learner's experience with other tools such as plagiarism detection, AI grading, coding graders, and others.

As the code is open, it is always possible to modify it. Still, it might result in a technical maintenance debt, which usually prevents educators from experimenting or installations from upgrading to newer versions once the changes to ORA become important in the teaching process.

Decisions
*********

As the first step towards making implementing new use cases during the ORA user's lifecycle more flexible, we will introduce two extension points in the ORA codebase. These extension points will be built on top of the `Hooks Extensions Framework`_. The definitions for these extension points will reside in `openedx-filters`_ and `openedx-events`_. These definitions will be imported into the edx-ora2 repository and triggered in two places during the learners' lifecycle, resulting in minimal modifications to the ORA implementation.

The first extension point we will implement is an `Open edX Filter`_ that will be executed before `rendering the submission HTML section of the block for the legacy view`_, with input arguments ``context`` and ``template path``. This implementation will allow us to modify what's rendered to the student, via the view ``context`` and ``template``, for cases when needed. 

The second extension point to be implemented is an `Open edX Event`_. It will be sent `after a student submits a response to the assessment`_ with the student's submission key data, like the ORA submission ID and files uploaded in the submission, as the event's payload. This event (that works like a notification) will allow us to take action after a submission is made based on the data sent.

Consequences
************

Extension developers often use those extension points in Open edX plugins to enhance the functionality of an existing application. When installing edx-ora2, developers can implement more use cases out-of-the-box by configuring it with plugins that use these extension points. These use cases include modify the context passed to ``legacy/response/oa_response.html`` , changing the template that is rendered to the student, and sending students' submission data to another service.

For instance, if a developer wants to add an acknowledgment notice to the submission template, they can implement a `pipeline step`_ for the filter that modifies the ``oa_response.html`` template for an ``oa_response_ack_modified.html`` template with its custom context. See `how to implement pipeline steps`_ for more information. To act on the submission-created notification, the developer can listen to the Open edX event since the event payload has enough information to get the student's submissions, including files, enabling the event receiver to obtain and send the submission to another service for analysis. See `how to listen for Open edX Events`_ for more information. 

These changes allow extension developers to interact with a crucial part of the student's assessment lifecycle. However, when none of these extension points are configured, ORA assessments will behave as usual. This first step sets a precedent for ORA developers to implement more extension points during the ORA users' lifecycle, enabling additional use cases to be built on top of them.

The extension points proposed in this PR are intended to facilitate the integration with tools for students' response analysis like Turnitin.These two extensions are designed to share information, not to give feedback to the user; other hooks and mechanisms might be implemented to do so. For more information on this use case, please refer to the `Platform Plugin Turnitin`_ documentation.

Rejected Alternatives
*********************

As suggested in the `platform roadmap GH ticket`_ for this feature, the team who wrote this ADR researched the feasibility of adding a new `External Tool Step`. Although this was considered the best option since ORA design entertained extension via customization and addition of workflow steps, it was rejected due to time constraints. Therefore, in this ADR, we only commit to implementing a lightweight extension mechanism because we understand the required effort. However, there is no technical limit on this proposal's growth into more support of a broad array of extension use cases.

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
.. _Platform Plugin Turnitin: https://github.com/eduNEXT/platform-plugin-turnitin
