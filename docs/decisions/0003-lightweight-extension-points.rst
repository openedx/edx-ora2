Lightweight extension points
############################

Status
******

**Draft** *2024-02-27*

Context
*******

Open-ended questions are commonly used in education for assessment purposes, but their flexible nature can facilitate cheating. Therefore, instructors need a way of assessing when cheating happens when reviewing responses. One widely-used solution to this problem in the academic field is the use online plagiarism tools by instructors. These tools receive the students' responses, analyze them, and provide reports that assist instructors in scoring.

No standard exists for ORA to facilitate integration with tools that process students' answers for plagiarism or other useful reports for the course staff. Therefore, ORA must allow external interactions with students' responses so they can be sent for analysis.

Decision
********

We'll enable external interactions with students' responses by using the `Hooks Extensions Framework`_. Using this approach, we'll implement extension points with minimal modifications in the edx-ora2 repository, making interventions with the students' response lifecycle possible. This is an interim solution for the problem stated above while the community develops a more sophisticated process that covers more use cases. This approach includes implementing two extension points:

- For the first extension point we will use an `Open edX Filter`_ with the following definition:

.. code::
  
  class ORASubmissionViewRenderStarted(OpenEdxPublicFilter):
      """
      Custom class used to create ORA submission view filters and its custom methods.
      """
  
      filter_type = "org.openedx.learning.ora.submission_view.render.started.v1"
  
      @classmethod
      def run_filter(cls, context: dict, template_name: str):
          """
          Execute a filter with the signature specified.
          Arguments:
              context (dict): context dictionary for submission view template.
              template_name (str): template name to be rendered by the student's dashboard.
          """
          data = super().run_pipeline(context=context, template_name=template_name, )
          return data.get("context"), data.get("template_name")

Triggered implemented before `rendering the submission HTML section of the block for the legacy view`_:

.. code::

    if path == "legacy/response/oa_response.html":
        try:
            # .. filter_implemented_name: ORASubmissionViewRenderStarted
            # .. filter_type: org.openedx.learning.ora.submission_view.render.started.v1
            context, path = ORASubmissionViewRenderStarted.run_filter(context, path)
        except ORASubmissionViewRenderStarted.RenderInvalidTemplate as exc:
            context, path = exc.context, exc.template_name

This implementation will allow us to modify what's rendered to the student, via the view context and template, for cases when needed. For example, some third-party services need acknowledgment before receiving users' information.

- The second extension point will be an Open edX Event. The event payload should contain enough information for later processing; in this case, we'll the following event definition:

.. code::

    attr.s(frozen=True)
    class ORASubmissionData:
        """
        Attributes defined to represent event when a user submits an ORA assignment.

        Arguments:
            id (str): identifier of the ORA submission.
            file_downloads (List[dict]): list of related files in the ORA submission. Each dict
                contains the following keys:
                    * download_url (str): URL to download the file.
                    * description (str): Description of the file.
                    * name (str): Name of the file.
                    * size (int): Size of the file.
        """
        id = attr.ib(type=str)
        file_downloads = attr.ib(type=List[dict], factory=list)

    # .. event_type: org.openedx.learning.ora.submission.created.v1
    # .. event_name: ORA_SUBMISSION_CREATED
    # .. event_description: Emitted when a new ORA submission is created
    # .. event_data: ORASubmissionData
    ORA_SUBMISSION_CREATED = OpenEdxPublicSignal(
        event_type="org.openedx.learning.ora.submission.created.v1",
        data={
            "submission": ORASubmissionData,
        },
    )

The event will be sent `after a student submits a response to the assessment`_ so it has access to the student's submission key data:

.. code::

    @staticmethod
    def send_ora_submission_created_event(submission: dict) -> None:
        """
        Send an event when a submission is created
        Args:
            submission (dict): The submission data
        """
        from openassessment.xblock.openassessmentblock import OpenAssessmentBlock

        file_downloads = OpenAssessmentBlock.get_download_urls_from_submission(
            submission
        )
        ORA_SUBMISSION_CREATED.send_event(
            submission=ORASubmissionData(
                id=submission.get("uuid"),
                file_downloads=file_downloads,
            )
        )

     ...

     self.send_ora_submission_created_event(submission)


Consequences
************

Extension developers commonly use those extension points in Open edX plugins to extend the functionality of an existing application, like the LMS. So, when installing edx-ora2 in the LMS with these changes alongside a plugin configured to use them, ORA extension developers will be able to:

- Modify the context passed to ``legacy/response/oa_response.html`` 
- Change the template that is rendered to the student
- Send students' submission data to another service

Let's say you want to add an acknowledgment notice to your submission template so students know their information is being shared with third-party services when submitting a response. The extension developer could implement a `pipeline step`_ for the filter that changes the ``oa_response.html`` template for an ``oa_response_ack_modified.html`` template with its context:

.. code::

    from openedx_filters import PipelineStep
    
    
    class ORASubmissionViewTurnitinWarning(PipelineStep):
        """Add warning message about Turnitin to the ORA submission view."""
    
        def run_filter(  # pylint: disable=unused-argument, disable=arguments-differ
            self, context: dict, template_name: str
        ) -> dict:
            """
            Execute filter that loads the submission template with a warning message that
            notifies the user that the submission will be sent to Turnitin.
    
            Args:
                context (dict): The context dictionary.
                template_name (str): ORA template name.
    
            Returns:
                dict: The context dictionary and the template name.
            """
            return {
                "context": context,
                "template_name": "some_plugin/oa_response_with_acknowledgement.html",
            }

See `how to implement pipeline steps`_ for more information. Now, by listening to the `Open edX Event`_, the developer could act on the submission-created notification. Since the event payload has enough information to get the student's submissions, including files, the event receiver can obtain the submission to send it to another service for analysis:

.. code::

    from some_plugin.tasks import ora_submission_created_processing_task

    @receiver(ORA_SUBMISSION_CREATED)
    def ora_submission_created(submission, **kwargs):
        """
        Handle the ORA_SUBMISSION_CREATED event.
    
        Args:
            submission (ORASubmissionData): The ORA submission data.
        """
        ora_submission_created_processing_task.delay(
            submission.id,
            submission.file_downloads,
        )

See `how to listen for Open edX Events`_ for more information. Extension developers could interact with an essential part of the student's assessment lifecycle with these changes. But when none of these extension points are configured for use, then ORA assessments will behave as usual.

Rejected Alternatives
*********************

As suggested in the `platform roadmap GH ticket`_ for this feature, the team researched the feasibility of adding a new pluggable assessment step. Although this was considered the best option since ORA design entertained extension via
customization and addition to the workflow step, it was concluded that the more straightforward solution was implementing a lightweight extension mechanism. 

.. _Hooks Extensions Framework: https://open-edx-proposals.readthedocs.io/en/latest/architectural-decisions/oep-0050-hooks-extension-framework.html
.. _rendering the submission HTML section of the block for the legacy view: https://github.com/openedx/edx-ora2/blob/master/openassessment/xblock/ui_mixins/legacy/views/submission.py#L19
.. _Open edX Filter: https://docs.openedx.org/projects/openedx-filters/en/latest/
.. _Open edX Event: https://docs.openedx.org/projects/openedx-filters/en/latest/
.. _pipeline step: https://docs.openedx.org/projects/openedx-filters/en/latest/concepts/glossary.html#pipeline-steps
.. _how to implement pipeline steps: https://docs.openedx.org/projects/openedx-filters/en/latest/how-tos/using-filters.html#implement-pipeline-steps
.. _how to listen for Open edX Events: https://docs.openedx.org/projects/openedx-events/en/latest/how-tos/using-events.html#receiving-events
.. _after a student submits a response to the assessment: https://github.com/openedx/edx-ora2/blob/master/openassessment/xblock/ui_mixins/legacy/handlers_mixin.py#L67
.. _`platform roadmap GH ticket`: https://github.com/openedx/platform-roadmap/issues/253
