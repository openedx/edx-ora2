"""
The Staff Area View mixin renders all the staff-specific information used to
determine the flow of the problem.
"""
from __future__ import absolute_import

import copy
from django.core.exceptions import ObjectDoesNotExist
from functools import wraps
import logging

from openassessment.assessment.errors import PeerAssessmentInternalError
from openassessment.workflow.errors import AssessmentWorkflowError, AssessmentWorkflowInternalError
from openassessment.xblock.data_conversion import create_submission_dict, list_to_conversational_format
from openassessment.xblock.resolve_dates import DISTANT_FUTURE, DISTANT_PAST
from submissions.errors import SubmissionNotFoundError, TeamSubmissionNotFoundError
from xblock.core import XBlock

from .user_data import get_user_preferences

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


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
            return func(xblock, *args, **kwargs)
        return _wrapped
    return _decorator


class StaffAreaMixin:
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

        # Include Latex setting
        context['allow_latex'] = self.allow_latex
        context['prompts_type'] = self.prompts_type

        # Include release/due dates for each step in the problem
        context['step_dates'] = list()
        for step in ['submission'] + self.assessment_steps:

            # Get the dates as a student would see them
            __, __, start_date, due_date = self.is_closed(
                step=step, course_staff=False)  # pylint: disable=redeclared-assigned-name

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

        # Include whether or not this is a team assignment
        context['is_team_assignment'] = self.is_team_assignment()

        context['xblock_id'] = self.get_xblock_id()
        return path, context

    @staticmethod
    def get_staff_assessment_statistics_context(course_id, item_id):
        """
        Returns a context with staff assessment "ungraded" and "in-progress" counts.
        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import staff as staff_api
        grading_stats = staff_api.get_staff_grading_statistics(course_id, item_id)

        return {
            'staff_assessment_ungraded': grading_stats['ungraded'],
            'staff_assessment_in_progress': grading_stats['in-progress']
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
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import staff as staff_api
        from submissions import api as submission_api
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
                    # Add team info to context
                    submission_context['teams_enabled'] = self.teams_enabled
                    if self.teams_enabled:
                        user = self.get_real_user(anonymous_student_id)

                        if not user:
                            logger.error(
                                '{}: User lookuip for anonymous_user_id {} failed'.format(
                                    self.location,
                                    anonymous_student_id
                                )
                            )
                            raise ObjectDoesNotExist()

                        team = self.teams_service.get_team(user, self.course_id, self.selected_teamset_id)

                        submission_context['team_name'] = team.name
                        submission_context['team_usernames'] = list_to_conversational_format(
                            [user.username for user in team.users.all()]
                        )

                    path = 'openassessmentblock/staff_area/oa_staff_grade_learners_assessment.html'
                    return self.render_assessment(path, submission_context)
                return self.render_error(self._(u"Error loading the checked out learner response."))
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
        user_preferences = get_user_preferences(self.runtime.service(self, 'user'))  # localize for staff user

        context = {
            'submission': create_submission_dict(submission, self.prompts) if submission else None,
            'rubric_criteria': copy.deepcopy(self.rubric_criteria_with_labels),
            'student_username': student_username,
            'user_timezone': user_preferences['user_timezone'],
            'user_language': user_preferences['user_language'],
            "prompts_type": self.prompts_type,
            "is_team_assignment": self.is_team_assignment(),
        }

        if submission:
            context["file_upload_type"] = self.file_upload_type
            context["staff_file_urls"] = self.get_download_urls_from_submission(submission)
            if self.should_use_user_state(context["staff_file_urls"]):
                logger.info(u"Checking student module for upload info for user: {username} in block: {block}".format(
                    username=student_username,
                    block=str(self.location)
                ))
                context['staff_file_urls'] = self.get_files_info_from_user_state(student_username)

                # This particular check is for the cases affected by the incorrect filenum bug
                # and gets all the upload URLs if feature enabled.
                if self.should_get_all_files_urls(context['staff_file_urls']):
                    logger.info(
                        u"Retrieving all uploaded files by user:{username} in block:{block}".format(
                            username=student_username,
                            block=str(self.location)
                        ))
                    context['staff_file_urls'] = self.get_all_upload_urls_for_user(student_username)

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
        # Import is placed here to avoid model import at project startup.
        from submissions import api as submission_api

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

        # Add team info to context
        context['team_name'] = None
        if anonymous_user_id and self.is_team_assignment():
            try:
                context['team_name'] = getattr(self.get_team_for_anonymous_user(anonymous_user_id), 'name', None)
            except ObjectDoesNotExist:
                # A student outside of the course will not exist and is valid
                pass

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
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api
        from openassessment.assessment.api import self as self_api
        from openassessment.assessment.api import staff as staff_api

        assessment_steps = self.assessment_steps

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
        grade_utils = self.runtime._services.get('grade_utils')  # pylint: disable=protected-access

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

        if grade_exists:
            if staff_assessment:
                staff_assessment_grade_context = self._assessment_grade_context(staff_assessment)

            grade_details = self.grade_details(
                submission_uuid,
                peer_assessments_grade_context,
                self_assessment_grade_context,
                staff_assessment_grade_context,
                is_staff=True,
            )

        workflow_cancellation = self.get_workflow_cancellation_info(submission_uuid)

        context.update({
            'self_assessment': [self_assessment] if self_assessment else None,
            'peer_assessments': peer_assessments,
            'staff_assessment': [staff_assessment] if staff_assessment else None,
            'submitted_assessments': submitted_assessments,
            'grade_details': grade_details,
            'score': workflow.get('score'),
            'workflow_status': workflow.get('status'),
            'workflow_cancellation': workflow_cancellation,
            'are_grades_frozen': grade_utils.are_grades_frozen() if grade_utils else None
        })

        if peer_assessments or self_assessment or staff_assessment:
            max_scores = peer_api.get_rubric_max_scores(submission_uuid)
            for criterion in context["rubric_criteria"]:
                criterion["total_value"] = max_scores[criterion["name"]]

    def clear_student_state(self, user_id, course_id, item_id, requesting_user_id):
        """
        This xblock method is called (from our LMS runtime, which defines this method signature) to clear student state
        for a given problem. It will cancel the workflow using traditional methods to remove it from the grading pools,
        and pass through to the submissions API to orphan the submission so that the user can create a new one.
        """

        if self.is_team_assignment():
            self.clear_team_state(user_id, course_id, item_id, requesting_user_id)
            return

        # Import is placed here to avoid model import at project startup.
        from submissions import api as submission_api
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
                clear_state=True
            )

    def clear_team_state(self, user_id, course_id, item_id, requesting_user_id):
        """
        This is called from clear_student_state (which is called from the LMS runtime) when the xblock is a team
        assignment, to clear student state for an entire team for a given problem. It will cancel the workflow
        to remove it from the grading pools, and pass through to the submissions team API to orphan the team
        submission and individual submissions so that the team can create a new submission.
        """
        error_msg_base = 'Attempted to clear team state for anonymous user {} '.format(user_id)
        try:
            user_team = self.get_team_for_anonymous_user(user_id)
        except ObjectDoesNotExist:
            warning_msg = error_msg_base + 'but was unable to resolve to a real user'
            logger.warning(warning_msg)
            return

        if user_team is None:
            warning_msg = error_msg_base + 'but they are not on a team for course {} item {}.'.format(
                course_id, item_id
            )
            logger.warning(warning_msg)
            return

        from submissions import team_api as team_submissions_api

        try:
            team_submission = team_submissions_api.get_team_submission_for_team(course_id, item_id, user_team.team_id)
        except TeamSubmissionNotFoundError:
            warning_msg = error_msg_base + "course {} item {} but no team submission was found for team {}".format(
                course_id, item_id, user_team.team_id
            )
            logger.warning(warning_msg)

        # Remove the submission from grading pool
        self._cancel_team_workflow(
            team_submission['team_submission_uuid'],
            "Student and team state cleared",
            requesting_user_id
        )
        # Tell the submissions API to orphan the submissions to prevent them from being accessed
        team_submissions_api.reset_scores(team_submission['team_submission_uuid'])

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

        if self.is_team_assignment():
            return self._cancel_team_submission(submission_uuid, comments)
        else:
            return self._cancel_workflow(submission_uuid, comments)

    def _cancel_team_submission(self, submission_uuid, comments):
        """
        Cancels a team submission given an individual submission's uuid
        """
        not_found_msg = self._('Submission not found')
        # Look up serialized individual submission to get team_submission_uuid
        try:
            submission = self.get_user_submission(submission_uuid)
        except SubmissionNotFoundError:
            return {"success": False, "msg": not_found_msg}
        if not submission:
            return {"success": False, "msg": not_found_msg}

        team_submission_uuid = submission.get('team_submission_uuid', None)
        if not team_submission_uuid:
            msg = self._('Submission for team assignment has no associated team submission')
            return {"success": False, "msg": msg}

        return self._cancel_team_workflow(str(team_submission_uuid), comments)

    def _cancel_workflow(self, submission_uuid, comments, requesting_user_id=None):
        """
        Internal helper method to cancel a workflow using the workflow API.

        If requesting_user is not provided, we will use the user to which this xblock is currently bound.
        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.workflow import api as workflow_api
        try:
            assessment_requirements = self.workflow_requirements()
            if requesting_user_id is None:
                # The student_id is actually the bound user, which is the staff user in this context.
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
            msg = str(ex)
            logger.exception(msg)
            return {"success": False, 'msg': msg}

    def _cancel_team_workflow(self, team_submission_uuid, comments, requesting_user_id=None):
        """
        Internal helper method to cancel a team workflow using the team workflow API.

        If requesting_user is not provided, we will use the user to which this xblock is currently bound.
        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.workflow import team_api as team_workflow_api
        try:
            if requesting_user_id is None:
                # The student_id is actually the bound user, which is the staff user in this context.
                requesting_user_id = self.get_student_item_dict()["student_id"]
            # Cancel the related workflow.
            team_workflow_api.cancel_workflow(
                team_submission_uuid,
                comments,
                requesting_user_id,
            )
            return {
                "success": True,
                'msg': self._(
                    "The team’s submission has been removed from grading. "
                    "The team receives a grade of zero unless you delete "
                    "a team member’s state for the problem to allow the team "
                    "to resubmit a response."
                )
            }
        except (
                AssessmentWorkflowError,
                AssessmentWorkflowInternalError
        ) as ex:
            msg = str(ex)
            logger.exception(msg)
            return {"success": False, 'msg': msg}
