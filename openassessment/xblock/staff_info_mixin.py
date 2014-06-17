"""
The Staff Info View mixin renders all the staff-specific information used to
determine the flow of the problem.
"""
import copy
from functools import wraps
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from xblock.core import XBlock
from openassessment.assessment.errors.ai import AIError
from openassessment.xblock.resolve_dates import DISTANT_PAST, DISTANT_FUTURE
from openassessment.xblock.data_conversion import (
    create_rubric_dict, convert_training_examples_list_to_dict
)
from submissions import api as submission_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import ai as ai_api


def require_global_admin(error_msg):
    """
    Method decorator to restrict access to an XBlock handler
    to only global staff.

    Args:
        error_msg (unicode): The error message to display to the user
        if they do not have sufficient permissions.

    Returns:
        Decorated function

    """
    def _decorator(func):   # pylint: disable=C0111
        @wraps(func)
        def _wrapped(xblock, *args, **kwargs):  # pylint: disable=C0111
            if not xblock.is_admin or xblock.in_studio_preview:
                return {'success': False, 'msg': unicode(error_msg)}
            else:
                return func(xblock, *args, **kwargs)
        return _wrapped
    return _decorator


def require_course_staff(error_msg):
    """
    Method decorator to restrict access to an XBlock render
    method to only course staff.

    Args:
        error_msg (unicode): The error message to display to the user
        if they do not have sufficient permissions.

    Returns:
        decorated function

    """
    def _decorator(func):  # pylint: disable=C0111
        @wraps(func)
        def _wrapped(xblock, *args, **kwargs):  # pylint: disable=C0111
            if not xblock.is_course_staff or xblock.in_studio_preview:
                return xblock.render_error(unicode(error_msg))
            else:
                return func(xblock, *args, **kwargs)
        return _wrapped
    return _decorator


class StaffInfoMixin(object):
    """
    Display debug information to course and global staff.
    """

    @XBlock.handler
    @require_course_staff(ugettext_lazy(u"You do not have permission to access staff information"))
    def render_staff_info(self, data, suffix=''):   # pylint: disable=W0613
        """
        Template context dictionary for course staff debug panel.

        Returns:
            dict: The template context specific to the course staff debug panel.

        """
        path, context = self.get_staff_path_and_context()
        return self.render_assessment(path, context)

    def get_staff_path_and_context(self):
        """
        Gets the path and context for the staff section of the ORA XBlock.
        """
        context = {}
        path = 'openassessmentblock/staff_debug/staff_debug.html'

        student_item = self.get_student_item_dict()

        # We need to display the new-style locations in the course staff
        # info, even if we're using old-style locations internally,
        # so course staff can use the locations to delete student state.
        context['item_id'] = student_item["item_id"]

        # Calculate how many students are in each step of the workflow
        status_counts, num_submissions = self.get_workflow_status_counts()
        context['status_counts'] = status_counts
        context['num_submissions'] = num_submissions

        # Show the schedule training button if example based assessment is
        # configured, and the current user has admin privileges.
        example_based_assessment = self.get_assessment_module('example-based-assessment')
        display_ai_staff_info = (
            self.is_admin and
            bool(example_based_assessment) and
            not self.in_studio_preview
        )
        context['display_schedule_training'] = display_ai_staff_info
        context['display_reschedule_unfinished_tasks'] = display_ai_staff_info
        if display_ai_staff_info:
            context['classifierset'] = ai_api.get_classifier_set_info(
                create_rubric_dict(self.prompt, self.rubric_criteria),
                example_based_assessment['algorithm_id'],
                student_item['course_id'],
                student_item['item_id']
            )

        # Include release/due dates for each step in the problem
        context['step_dates'] = list()

        steps = ['submission'] + self.assessment_steps
        for step in steps:

            if step == 'example-based-assessment':
                continue

            # Get the dates as a student would see them
            __, __, start_date, due_date = self.is_closed(step=step, course_staff=False)

            context['step_dates'].append({
                'step': step,
                'start': start_date if start_date > DISTANT_PAST else None,
                'due': due_date if due_date < DISTANT_FUTURE else None,
            })
        return path, context

    @XBlock.json_handler
    @require_global_admin(ugettext_lazy(u"You do not have permission to schedule training"))
    def schedule_training(self, data, suffix=''):   # pylint: disable=W0613
        """
        Schedule a new training task for example-based grading.
        """
        assessment = self.get_assessment_module('example-based-assessment')
        student_item_dict = self.get_student_item_dict()

        if assessment:
            examples = assessment["examples"]
            try:
                workflow_uuid = ai_api.train_classifiers(
                    create_rubric_dict(self.prompt, self.rubric_criteria),
                    convert_training_examples_list_to_dict(examples),
                    student_item_dict.get('course_id'),
                    student_item_dict.get('item_id'),
                    assessment["algorithm_id"]
                )
                return {
                    'success': True,
                    'workflow_uuid': workflow_uuid,
                    'msg': _(u"Training scheduled with new Workflow UUID: {uuid}".format(uuid=workflow_uuid))
                }
            except AIError as err:
                return {
                    'success': False,
                    'msg': _(u"An error occurred scheduling classifier training: {error}".format(error=err))
                }

        else:
            return {
                'success': False,
                'msg': _(u"Example Based Assessment is not configured for this location.")
            }

    @XBlock.handler
    @require_course_staff(ugettext_lazy(u"You do not have permission to access student information."))
    def render_student_info(self, data, suffix=''): # pylint: disable=W0613
        """
        Renders all relative information for a specific student's workflow.

        Given a student's ID, we can render a staff-only section of the page
        with submissions and assessments specific to the student.

        Must be course staff to render this view.

        """
        path, context = self.get_student_info_path_and_context(data)
        return self.render_assessment(path, context)

    def get_student_info_path_and_context(self, data):
        """
        Get the proper path and context for rendering the the student info
        section of the staff debug panel.

        """
        student_id = data.params.get('student_id', '')
        submission_uuid = None
        submission = None
        assessment_steps = self.assessment_steps

        if student_id:
            student_item = self.get_student_item_dict()
            student_item['student_id'] = student_id

            # If there is a submission available for the requested student, present
            # it. If not, there will be no other information to collect.
            submissions = submission_api.get_submissions(student_item, 1)

            if submissions:
                submission = submissions[0]
                submission_uuid = submissions[0]['uuid']

        example_based_assessment = None
        self_assessment = None
        peer_assessments = []
        submitted_assessments = []

        if "peer-assessment" in assessment_steps:
            peer_assessments = peer_api.get_assessments(submission_uuid)
            submitted_assessments = peer_api.get_submitted_assessments(submission_uuid, scored_only=False)

        if "self-assessment" in assessment_steps:
            self_assessment = self_api.get_assessment(submission_uuid)

        if "example-based-assessment" in assessment_steps:
            example_based_assessment = ai_api.get_latest_assessment(submission_uuid)

        context = {
            'submission': submission,
            'peer_assessments': peer_assessments,
            'submitted_assessments': submitted_assessments,
            'self_assessment': self_assessment,
            'example_based_assessment': example_based_assessment,
            'rubric_criteria': copy.deepcopy(self.rubric_criteria),
        }

        if peer_assessments or self_assessment or example_based_assessment:
            max_scores = peer_api.get_rubric_max_scores(submission_uuid)
            for criterion in context["rubric_criteria"]:
                criterion["total_value"] = max_scores[criterion["name"]]

        path = 'openassessmentblock/staff_debug/student_info.html'
        return path, context

    @XBlock.json_handler
    @require_global_admin(ugettext_lazy(u"You do not have permission to reschedule tasks."))
    def reschedule_unfinished_tasks(self, data, suffix=''):  # pylint: disable=W0613
        """
        Wrapper which invokes the API call for rescheduling grading tasks.

        Checks that the requester is an administrator that is not in studio-preview mode,
        and that the api-call returns without error.  If it returns with an error, (any
        exception), the appropriate JSON serializable dictionary with success conditions
        is passed back.

        Args:
            data (not used)
            suffix (not used)

        Return:
            Json serilaizable dict with the following elements:
                'success': (bool) Indicates whether or not the tasks were rescheduled successfully
                'msg': The response to the server (could be error message or success message)
        """
        # Identifies the course and item that will need to be re-run
        student_item_dict = self.get_student_item_dict()
        course_id = student_item_dict.get('course_id')
        item_id = student_item_dict.get('item_id')

        try:
            # Note that we only want to recschdule grading tasks, but maintain the potential functionallity
            # within the API to also reschedule training tasks.
            ai_api.reschedule_unfinished_tasks(course_id=course_id, item_id=item_id, task_type=u"grade")
            return {
                'success': True,
                'msg': _(u"All AI tasks associated with this item have been rescheduled successfully.")
            }
        except AIError as ex:
            return {
                'success': False,
                'msg': _(u"An error occurred while rescheduling tasks: {}".format(ex))
            }
