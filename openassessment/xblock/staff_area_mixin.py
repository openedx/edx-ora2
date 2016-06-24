"""
The Staff Area View mixin renders all the staff-specific information used to
determine the flow of the problem.
"""
import copy
from functools import wraps
import logging

from xblock.core import XBlock
from openassessment.assessment.errors import (
    PeerAssessmentInternalError,
)
from openassessment.workflow.errors import (
    AssessmentWorkflowError, AssessmentWorkflowInternalError
)
from openassessment.assessment.errors.ai import AIError
from openassessment.xblock.resolve_dates import DISTANT_PAST, DISTANT_FUTURE
from openassessment.xblock.data_conversion import (
    create_rubric_dict, convert_training_examples_list_to_dict, create_submission_dict
)
from submissions import api as submission_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import ai as ai_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.api import staff as staff_api


logger = logging.getLogger(__name__)


def require_global_admin(error_key):
    """
    Method decorator to restrict access to an XBlock handler
    to only global staff.

    Args:
        error_key (str): The key to the error message to display to the user
        if they do not have sufficient permissions.

    Returns:
        Decorated function

    """
    def _decorator(func):  # pylint: disable=C0111
        @wraps(func)
        def _wrapped(xblock, *args, **kwargs):  # pylint: disable=C0111
            permission_errors = {
                "SCHEDULE_TRAINING": xblock._(u"You do not have permission to schedule training"),
                "RESCHEDULE_TASKS": xblock._(u"You do not have permission to reschedule tasks."),
            }
            if not xblock.is_admin or xblock.in_studio_preview:
                return {'success': False, 'msg': permission_errors[error_key]}
            else:
                return func(xblock, *args, **kwargs)
        return _wrapped
    return _decorator


def require_course_staff(error_key, with_json_handler=False):
    """
    Method decorator to restrict access to an XBlock render
    method to only course staff.

    Args:
        error_key (str): The key for the error message to display to the
            user if they do not have sufficient permissions.

    Returns:
        decorated function

    """
    def _decorator(func):  # pylint: disable=C0111
        @wraps(func)
        def _wrapped(xblock, *args, **kwargs):  # pylint: disable=C0111
            permission_errors = {
                "STAFF_AREA": xblock._(u"You do not have permission to access the ORA staff area"),
                "STUDENT_INFO": xblock._(u"You do not have permission to access ORA learner information."),
                "STUDENT_GRADE": xblock._(u"You do not have permission to access ORA staff grading."),
            }

            if not xblock.is_course_staff and with_json_handler:
                return {"success": False, "msg": permission_errors[error_key]}
            elif not xblock.is_course_staff or xblock.in_studio_preview:
                return xblock.render_error(permission_errors[error_key])
            else:
                return func(xblock, *args, **kwargs)
        return _wrapped
    return _decorator


class StaffAreaMixin(object):
    """
    Display debug information to course and global staff.
    """

    @XBlock.handler
    @require_course_staff("STAFF_AREA")
    def render_staff_area(self, data, suffix=''):  # pylint: disable=W0613
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
        path = 'openassessmentblock/staff_area/oa_staff_area.html'

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
                create_rubric_dict(self.prompts, self.rubric_criteria_with_labels),
                example_based_assessment['algorithm_id'],
                student_item['course_id'],
                student_item['item_id']
            )

        # Include Latex setting
        context['allow_latex'] = self.allow_latex

        # Include release/due dates for each step in the problem
        context['step_dates'] = list()
        for step in ['submission'] + self.assessment_steps:

            if step == 'example-based-assessment':
                continue

            # Get the dates as a student would see them
            __, __, start_date, due_date = self.is_closed(step=step, course_staff=False)

            context['step_dates'].append({
                'step': step,
                'start': start_date if start_date > DISTANT_PAST else None,
                'due': due_date if due_date < DISTANT_FUTURE else None,
            })

        # Include whether or not staff grading step is enabled.
        staff_assessment_required = "staff-assessment" in self.assessment_steps
        context['staff_assessment_required'] = staff_assessment_required
        if staff_assessment_required:
            context.update(
                self.get_staff_assessment_statistics_context(student_item["course_id"], student_item["item_id"])
            )

        context['xblock_id'] = self.get_xblock_id()
        return path, context

    @staticmethod
    def get_staff_assessment_statistics_context(course_id, item_id):
        """
        Returns a context with staff assessment "ungraded" and "in-progress" counts.
        """
        grading_stats = staff_api.get_staff_grading_statistics(course_id, item_id)

        return {
            'staff_assessment_ungraded': grading_stats['ungraded'],
            'staff_assessment_in_progress': grading_stats['in-progress']
        }

    @XBlock.json_handler
    @require_global_admin("SCHEDULE_TRAINING")
    def schedule_training(self, data, suffix=''):  # pylint: disable=W0613
        """
        Schedule a new training task for example-based grading.
        """
        assessment = self.get_assessment_module('example-based-assessment')
        student_item_dict = self.get_student_item_dict()

        if assessment:
            examples = assessment["examples"]
            try:
                workflow_uuid = ai_api.train_classifiers(
                    create_rubric_dict(self.prompts, self.rubric_criteria_with_labels),
                    convert_training_examples_list_to_dict(examples),
                    student_item_dict.get('course_id'),
                    student_item_dict.get('item_id'),
                    assessment["algorithm_id"]
                )
                return {
                    'success': True,
                    'workflow_uuid': workflow_uuid,
                    'msg': self._(u"Training scheduled with new Workflow UUID: {uuid}".format(uuid=workflow_uuid))
                }
            except AIError as err:
                return {
                    'success': False,
                    'msg': self._(u"An error occurred scheduling classifier training: {error}".format(error=err))
                }

        else:
            return {
                'success': False,
                'msg': self._(u"Example Based Assessment is not configured for this location.")
            }

    @XBlock.handler
    @require_course_staff("STUDENT_INFO")
    def render_student_info(self, data, suffix=''):  # pylint: disable=W0613
        """
        Renders all relative information for a specific student's workflow.

        Given a student's username, we can render a staff-only section of the page
        with submissions and assessments specific to the student.

        Must be course staff to render this view.

        """
        try:
            student_username = data.params.get('student_username', '')
            path, context = self.get_student_info_path_and_context(student_username)
            return self.render_assessment(path, context)

        except PeerAssessmentInternalError:
            return self.render_error(self._(u"Error getting learner information."))

    @XBlock.handler
    @require_course_staff("STUDENT_GRADE")
    def render_staff_grade_form(self, data, suffix=''):  # pylint: disable=W0613
        """
        Renders a form to staff-grade the next available learner submission.

        Must be course staff to render this view.
        """
        try:
            student_item_dict = self.get_student_item_dict()
            course_id = student_item_dict.get('course_id')
            item_id = student_item_dict.get('item_id')
            staff_id = student_item_dict['student_id']

            # Note that this will check out a submission for grading by the specified staff member.
            # If no submissions are available for grading, will return None.
            submission_to_assess = staff_api.get_submission_to_assess(course_id, item_id, staff_id)

            if submission_to_assess is not None:
                # This is posting a tracking event to the runtime.
                self.runtime.publish(self, 'openassessmentblock.get_submission_for_staff_grading', {
                    'type': 'full-grade',
                    'requesting_staff_id': staff_id,
                    'item_id': item_id,
                    'submission_returned_uuid': submission_to_assess['uuid']
                })
                submission = submission_api.get_submission_and_student(submission_to_assess['uuid'])
                if submission:
                    anonymous_student_id = submission['student_item']['student_id']
                    submission_context = self.get_student_submission_context(
                        self.get_username(anonymous_student_id), submission
                    )
                    path = 'openassessmentblock/staff_area/oa_staff_grade_learners_assessment.html'
                    return self.render_assessment(path, submission_context)
                else:
                    return self.render_error(self._(u"Error loading the checked out learner response."))
            else:
                return self.render_error(self._(u"No other learner responses are available for grading at this time."))

        except PeerAssessmentInternalError:
            return self.render_error(self._(u"Error getting staff grade information."))

    @XBlock.handler
    @require_course_staff("STUDENT_GRADE")
    def render_staff_grade_counts(self, data, suffix=''):  # pylint: disable=W0613
        """
        Renders a form to show the number of ungraded and checked out assessments.

        Must be course staff to render this view.
        """
        try:
            student_item_dict = self.get_student_item_dict()

            context = self.get_staff_assessment_statistics_context(
                student_item_dict.get('course_id'), student_item_dict.get('item_id')
            )

            path = 'openassessmentblock/staff_area/oa_staff_grade_learners_count.html'
            return self.render_assessment(path, context)

        except PeerAssessmentInternalError:
            return self.render_error(self._(u"Error getting staff grade ungraded and checked out counts."))

    def get_student_submission_context(self, student_username, submission):
        """
        Get a context dict for rendering a student submission and associated rubric (for staff grading).
        Includes submission (populating submitted file information if relevant), rubric_criteria,
        and student_username.

        Args:
            student_username (unicode): The username of the student to report.
            submission (object): A submission, as returned by the submission_api.

        Returns:
            A context dict for rendering a student submission and associated rubric (for staff grading).
        """
        context = {
            'submission': create_submission_dict(submission, self.prompts) if submission else None,
            'rubric_criteria': copy.deepcopy(self.rubric_criteria_with_labels),
            'student_username': student_username,
        }

        if submission:
            context["file_upload_type"] = self.file_upload_type
            context["staff_file_url"] = self.get_download_url_from_submission(submission)

        if self.rubric_feedback_prompt is not None:
            context["rubric_feedback_prompt"] = self.rubric_feedback_prompt

        if self.rubric_feedback_default_text is not None:
            context['rubric_feedback_default_text'] = self.rubric_feedback_default_text

        context['xblock_id'] = self.get_xblock_id()
        return context

    def get_student_info_path_and_context(self, student_username):
        """
        Get the proper path and context for rendering the student info
        section of the staff area.

        Args:
            student_username (unicode): The username of the student to report.
        """
        anonymous_user_id = None
        student_item = None
        submissions = None
        submission = None
        submission_uuid = None

        if student_username:
            anonymous_user_id = self.get_anonymous_user_id(student_username, self.course_id)
            student_item = self.get_student_item_dict(anonymous_user_id=anonymous_user_id)

        if anonymous_user_id:
            # If there is a submission available for the requested student, present
            # it. If not, there will be no other information to collect.
            submissions = submission_api.get_submissions(student_item, 1)

        if submissions:
            submission = submissions[0]
            submission_uuid = submission['uuid']

        # This will add submission (which may be None) and username to the context.
        context = self.get_student_submission_context(student_username, submission)

        # Only add the rest of the details to the context if a submission exists.
        if submission_uuid:
            self.add_submission_context(submission_uuid, context)

        path = 'openassessmentblock/staff_area/oa_student_info.html'
        return path, context

    def add_submission_context(self, submission_uuid, context):
        """
        Add the submission information (self asssessment, peer assessments, final grade, etc.)
        to the supplied context for display in the "learner info" portion of staff tools.
        Args:
            submission_uuid (unicode): The uuid of the submission, should NOT be None.
            context: the context to update with additional information
        """
        assessment_steps = self.assessment_steps

        example_based_assessment = None
        example_based_assessment_grade_context = None

        self_assessment = None
        self_assessment_grade_context = None

        peer_assessments = None
        peer_assessments_grade_context = []

        staff_assessment = staff_api.get_latest_staff_assessment(submission_uuid)
        staff_assessment_grade_context = None

        submitted_assessments = None

        grade_details = None

        workflow = self.get_workflow_info(submission_uuid=submission_uuid)
        grade_exists = workflow.get('status') == "done"

        if "peer-assessment" in assessment_steps:
            peer_assessments = peer_api.get_assessments(submission_uuid)
            submitted_assessments = peer_api.get_submitted_assessments(submission_uuid)
            if grade_exists:
                peer_api.get_score(submission_uuid, self.workflow_requirements()["peer"])
                peer_assessments_grade_context = [
                    self._assessment_grade_context(peer_assessment)
                    for peer_assessment in peer_assessments
                ]

        if "self-assessment" in assessment_steps:
            self_assessment = self_api.get_assessment(submission_uuid)
            if grade_exists:
                self_assessment_grade_context = self._assessment_grade_context(self_assessment)

        if "example-based-assessment" in assessment_steps:
            example_based_assessment = ai_api.get_latest_assessment(submission_uuid)
            if grade_exists:
                example_based_assessment_grade_context = self._assessment_grade_context(example_based_assessment)

        if grade_exists:
            if staff_assessment:
                staff_assessment_grade_context = self._assessment_grade_context(staff_assessment)

            grade_details = self.grade_details(
                submission_uuid,
                peer_assessments_grade_context,
                self_assessment_grade_context,
                example_based_assessment_grade_context,
                staff_assessment_grade_context,
                is_staff=True,
            )

        workflow_cancellation = self.get_workflow_cancellation_info(submission_uuid)

        context.update({
            'example_based_assessment': [example_based_assessment] if example_based_assessment else None,
            'self_assessment': [self_assessment] if self_assessment else None,
            'peer_assessments': peer_assessments,
            'staff_assessment': [staff_assessment] if staff_assessment else None,
            'submitted_assessments': submitted_assessments,
            'grade_details': grade_details,
            'score': workflow.get('score'),
            'workflow_status': workflow.get('status'),
            'workflow_cancellation': workflow_cancellation,
        })

        if peer_assessments or self_assessment or example_based_assessment or staff_assessment:
            max_scores = peer_api.get_rubric_max_scores(submission_uuid)
            for criterion in context["rubric_criteria"]:
                criterion["total_value"] = max_scores[criterion["name"]]

    @XBlock.json_handler
    @require_global_admin("RESCHEDULE_TASKS")
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
                'msg': self._(u"All AI tasks associated with this item have been rescheduled successfully.")
            }
        except AIError as ex:
            return {
                'success': False,
                'msg': self._(u"An error occurred while rescheduling tasks: {}".format(ex))
            }

    def clear_student_state(self, user_id, course_id, item_id, requesting_user_id):
        """
        This xblock method is called (from our LMS runtime, which defines this method signature) to clear student state
        for a given problem. It will cancel the workflow using traditional methods to remove it from the grading pools,
        and pass through to the submissions API to orphan the submission so that the user can create a new one.
        """
        # Note that student_item cannot be constructed using get_student_item_dict, since we're in a staff context
        student_item = {
            'course_id': course_id,
            'student_id': user_id,
            'item_id': item_id,
            'item_type': 'openassessment',
        }
        # There *should* only be one submission, but the logic is easy to extend for multiples so we may as well do it
        submissions = submission_api.get_submissions(student_item)
        for sub in submissions:
            # Remove the submission from grading pools
            self._cancel_workflow(sub['uuid'], "Student state cleared", requesting_user_id=requesting_user_id)

            # Tell the submissions API to orphan the submission to prevent it from being accessed
            submission_api.reset_score(
                user_id,
                course_id,
                item_id,
                clear_state=True  # pylint: disable=unexpected-keyword-arg
            )
            # TODO: try to remove the above pylint disable once edx-submissions release is done

    @XBlock.json_handler
    @require_course_staff("STUDENT_INFO", with_json_handler=True)
    def cancel_submission(self, data, suffix=''):  # pylint: disable=W0613
        """
        This will cancel the assessment + peer workflow for the particular submission.

        Args:
            data (dict): Data contain two attributes: submission_uuid and
                comments. submission_uuid is id of submission which is to be
                removed from the grading pool. Comments is the reason given
                by the user.

            suffix (not used)

        Return:
            Json serializable dict with the following elements:
                'success': (bool) Indicates whether or not the workflow cancelled successfully.
                'msg': The response (could be error message or success message).
        """
        submission_uuid = data.get('submission_uuid')
        comments = data.get('comments')

        if not comments:
            return {"success": False, "msg": self._(u'Please enter valid reason to remove the submission.')}

        return self._cancel_workflow(submission_uuid, comments)

    def _cancel_workflow(self, submission_uuid, comments, requesting_user_id=None):
        """
        Internal helper method to cancel a workflow using the workflow API.

        If requesting_user is not provided, we will use the user to which this xblock is currently bound.
        """
        try:
            assessment_requirements = self.workflow_requirements()
            if requesting_user_id is None:
                "The student_id is actually the bound user, which is the staff user in this context."
                requesting_user_id = self.get_student_item_dict()["student_id"]
            # Cancel the related workflow.
            workflow_api.cancel_workflow(
                submission_uuid=submission_uuid, comments=comments,
                cancelled_by_id=requesting_user_id,
                assessment_requirements=assessment_requirements
            )
            return {
                "success": True,
                'msg': self._(
                    u"The learner submission has been removed from peer assessment. "
                    u"The learner receives a grade of zero unless you delete "
                    u"the learner's state for the problem to allow them to "
                    u"resubmit a response."
                )
            }
        except (
                AssessmentWorkflowError,
                AssessmentWorkflowInternalError
        ) as ex:
            msg = ex.message
            logger.exception(msg)
            return {"success": False, 'msg': msg}
