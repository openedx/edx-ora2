"""
API endpoints for enhanced staff grader
"""
from functools import wraps
import logging

from django.db.models import Case, OuterRef, Prefetch, Subquery, Value, When
from django.db.models.fields import CharField
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from submissions.api import get_student_ids_by_submission_uuid, get_submission
from submissions.errors import SubmissionInternalError, SubmissionNotFoundError, SubmissionRequestError, SubmissionError

from openassessment.assessment.models.base import Assessment, AssessmentPart
from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.data import map_anonymized_ids_to_usernames
from openassessment.staffgrader.errors.submission_lock import SubmissionLockContestedError
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.staffgrader.serializers import (
    AssessmentSerializer,
    MissingContextException,
    SubmissionDetailFileSerilaizer,
    SubmissionListSerializer,
    SubmissionLockSerializer,
)
from openassessment.xblock.staff_area_mixin import require_course_staff
from openassessment.data import OraSubmissionAnswerFactory, VersionNotFoundException


log = logging.getLogger(__name__)


def require_submission_uuid(validate=True):
    """
    Unpacks and passes submission_uuid from request to handler function.

    params:
    - validate: Whether or not to check submissions to see if this is a real submission UUID or not. Default True

    Raises:
    - 400 if the submission_uuid was not provided or was incorrectly formatted
    - 404 if the submission_uuid wasn't found in submissions
    - 500 for errors with submissions or general exceptions
    """
    def decorator(handler):
        @wraps(handler)
        def wrapped_handler(self, data, suffix=""):  # pylint: disable=unused-argument
            submission_uuid = data.get('submission_uuid', None)
            if not submission_uuid:
                raise JsonHandlerError(400, "Body must contain a submission_uuid")
            if validate:
                try:
                    get_submission(submission_uuid)
                except SubmissionNotFoundError as exc:
                    raise JsonHandlerError(404, "Submission not found") from exc
                except SubmissionRequestError as exc:
                    raise JsonHandlerError(400, "Bad submission_uuid provided") from exc
                except (SubmissionInternalError, Exception) as exc:
                    raise JsonHandlerError(500, "Internal error getting submission info") from exc
            return handler(self, submission_uuid, data, suffix=suffix)
        return wrapped_handler
    return decorator


class StaffGraderMixin:
    """
    Actions to interact with submission locks, blocking other staff from grading assignments while
    grading is in progress.
    """

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    @require_submission_uuid(validate=False)
    def check_submission_lock(self, submission_uuid, data, suffix=""):  # pylint: disable=unused-argument
        """
        Get info about a submission lock. Does not verify that the ID is a valid submission.

        Returns:
        - Serialized submission lock info.
        """
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()
        context = {'user_id': anonymous_user_id}

        submission_lock = SubmissionGradingLock.get_submission_lock(submission_uuid) or {}
        return SubmissionLockSerializer(submission_lock, context=context).data

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    @require_submission_uuid(validate=True)
    def claim_submission_lock(self, submission_uuid, data, suffix=''):  # pylint: disable=unused-argument
        """
        Attempt to claim or reclaim a submission lock

        Returns:
        - Serialized submission lock info.

        Raises:
        - 403 in the case of a contested lock
        """
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()
        context = {'user_id': anonymous_user_id}

        try:
            submission_lock = SubmissionGradingLock.claim_submission_lock(submission_uuid, anonymous_user_id)
            return SubmissionLockSerializer(submission_lock, context=context).data
        except SubmissionLockContestedError as err:
            raise JsonHandlerError(403, err.get_error_code()) from err

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    @require_submission_uuid(validate=False)
    def delete_submission_lock(self, submission_uuid, data, suffix=''):  # pylint: disable=unused-argument
        """
        Attempt to clear a submission lock.

        Returns:
        - Serialized submission lock info (which in this case would just be {'lock_status': 'unlocked'})

        Raises:
        - 403 in the case of a contested lock
        """
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()
        context = {'user_id': anonymous_user_id}

        try:
            SubmissionGradingLock.clear_submission_lock(submission_uuid, anonymous_user_id)
            return SubmissionLockSerializer({}, context=context).data
        except SubmissionLockContestedError as err:
            raise JsonHandlerError(403, err.get_error_code()) from err

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def list_staff_workflows(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Returns data for the base "list" view, showing a summary of all graded / gradable items in the given assignment

        Example Data Shape:
        {
            submission_uuid:
        }
        """
        if self.is_team_assignment():
            raise JsonHandlerError(400, "Team Submissions not currently supported")

        # Fetch staff workflows, annotated with grading_status and lock_status
        staff_workflows = self._bulk_fetch_annotated_staff_workflows()
        # Lookup additional info like usernames and assessments
        serializer_context = self._get_list_workflows_serializer_context(staff_workflows)

        # Serialize workflows with the context, and return the dict of submissions
        result = {}
        for staff_workflow in staff_workflows:
            try:
                serialized_workflow = SubmissionListSerializer(staff_workflow, context=serializer_context).data
                result[staff_workflow.identifying_uuid] = serialized_workflow
            except MissingContextException as e:
                log.exception("Failed to serialize workflow %d: %s", staff_workflow.id, str(e), exc_info=True)
        return result

    def _get_list_workflows_serializer_context(self, staff_workflows):
        """
        Fetch additional required data and models to serialize the response
        """
        # Pull out three sets from the workflows for use later
        submission_uuids, workflow_scorer_ids, assessment_ids = set(), set(), set()
        for workflow in staff_workflows:
            submission_uuids.add(workflow.identifying_uuid)
            if workflow.assessment:
                assessment_ids.add(workflow.assessment)
            if workflow.scorer_id:
                workflow_scorer_ids.add(workflow.scorer_id)
        course_id = self.get_student_item_dict()['course_id']

        # Fetch user identifier mappings

        # When we look up usernames we want to include all connected learner student ids
        submission_uuid_to_student_id = get_student_ids_by_submission_uuid(
            course_id,
            submission_uuids,
        )

        # Do bulk lookup for all anonymous ids (submitters and scoreres). This is used for the
        # `gradedBy` and `username` fields
        anonymous_id_to_username = map_anonymized_ids_to_usernames(
            set(submission_uuid_to_student_id.values()) | workflow_scorer_ids
        )

        # Do a bulk fetch of the assessments linked to the workflows, including all connected
        # Rubric, Criteria, and Option models
        submission_uuid_to_assessment = self.bulk_deep_fetch_assessments(assessment_ids)
        return {
            'submission_uuid_to_student_id': submission_uuid_to_student_id,
            'anonymous_id_to_username': anonymous_id_to_username,
            'submission_uuid_to_assessment': submission_uuid_to_assessment,
        }

    def _bulk_fetch_annotated_staff_workflows(self):
        """
        Returns: QuerySet of StaffWorkflows, filtered by the current course and item, with the following annotations:
         - current_lock_user: The "owner_id" of the most recent active (created less than TIME_LIMIT ago) lock
         - grading_status: one of
                              * "graded"   - the StaffWorkflow has an associated Assessment
                              * "ungraded" - the StaffWorkflow has no asociated Assessment
        - lock_status: one of
                              * "in-progress" - current_lock_user is the current user's anonymous id.
                                                The current user has an active lock on this submission.
                              * "locked"      - current_lock_user is non-null and not the current user's anonymous id.
                                                Another user has an active lock on this submission.
                              * "unlocked"    - current_lock_user is null
                                                There is no active lock on this submission.
        """
        # Create an unevaluated QuerySet of "active" SubmissionLock objects that refer to the same submission as the
        # "current" workflow
        student_item_dict = self.get_student_item_dict()
        newest_lock = SubmissionGradingLock.currently_active().filter(
            submission_uuid=OuterRef('submission_uuid')
        ).order_by(
            '-created_at'
        )

        staff_workflows = StaffWorkflow.objects.filter(
            course_id=student_item_dict['course_id'],
            item_id=student_item_dict['item_id'],
            cancelled_at=None,
        ).annotate(
            current_lock_user=Subquery(newest_lock.values('owner_id')),
        ).annotate(
            grading_status=Case(
                When(assessment__isnull=False, then=Value("graded", output_field=CharField())),
                default=Value("ungraded", output_field=CharField())
            ),
            lock_status=Case(
                When(
                    current_lock_user=student_item_dict['student_id'],
                    then=Value("in-progress", output_field=CharField())
                ),
                When(
                    current_lock_user__isnull=False,
                    then=Value("locked", output_field=CharField())
                ),
                default=Value("unlocked", output_field=CharField())
            )
        )
        return staff_workflows

    def bulk_deep_fetch_assessments(self, assessment_ids):
        """
        Given a list of Assessment ids, fetch Assessments and prefetch
        linked Rubrics, AssessmentParts, Criteria, and Options.

        returns: (dict) mapping submission uuids to the associated assessment.
        If there is no assessment associated with a submission, it is not included in the dict.
        """
        assessments = Assessment.objects.filter(
            pk__in=assessment_ids
        ).prefetch_related(
            Prefetch(
                "parts",
                queryset=AssessmentPart.objects.select_related('criterion', 'option')
            ),
            "rubric__criteria",
            "rubric__criteria__options"

        ).select_related(
            'rubric',
        ).order_by('-scored_at')
        assessments_by_submission_uuid = {
            assessment.submission_uuid: assessment
            for assessment in assessments
        }
        return assessments_by_submission_uuid

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    @require_submission_uuid(validate=True)
    def get_submission_info(self, submission_uuid, _, suffix=''):  # pylint: disable=unused-argument
        """
        Return a dict representation of a submission in the form
        {
            'text': <list of strings representing the raw response for each prompt>
            'files': <list of:>
                {
                    'download_url': <file url>
                    'description': <file description>
                    'name': <file name>
                }
        }
        """
        try:
            submission = get_submission(submission_uuid)
            answer = OraSubmissionAnswerFactory.parse_submission_raw_answer(submission.get('answer'))
        except SubmissionError as err:
            raise JsonHandlerError(404, str(err)) from err
        except VersionNotFoundException as err:
            raise JsonHandlerError(500, str(err)) from err

        return {
            'files': [
                SubmissionDetailFileSerilaizer(file_data).data
                for file_data in self.get_download_urls_from_submission(submission)
            ],
            'text': answer.get_text_responses()
        }

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    @require_submission_uuid(validate=True)
    def get_assessment_info(self, submission_uuid, _, suffix=''):  # pylint: disable=unused-argument
        """
        Returns a dict representation of a staff assessment in the form
        {
            'feedback': <submission-level feedback>
            'points_earned': <earned points>
            'points_possible': <maximum possible points>
            'criteria': list of {
                'name': <criterion name>
                'option': <name of selected option> This may be blank.
                          If so, there are no options defined for the given criterion and it is feedback-only
                'feedback': <feedback for criterion>
            }
        }
        """
        student_item_dict = self.get_student_item_dict()
        course_id = student_item_dict['course_id']
        item_id = student_item_dict['item_id']
        try:
            workflow = StaffWorkflow.get_staff_workflow(course_id, item_id, submission_uuid)
        except StaffWorkflow.DoesNotExist as ex:
            msg = f"No gradeable submission found with uuid={submission_uuid} in course={course_id} item={item_id}"
            raise JsonHandlerError(404, msg) from ex

        if not workflow.assessment:
            return {}

        assessments = self.bulk_deep_fetch_assessments([workflow.assessment])
        if len(assessments) != 1 or submission_uuid not in assessments:
            log.error(
                (
                    "[%s] Error looking up assessments. Submission UUID = %s, "
                    "Staff Workflow Id = %d, Staff Workflow Assessment = %s, Assessments = %s"
                ),
                item_id, submission_uuid, workflow.id, workflow.assessment, assessments
            )
            raise JsonHandlerError(500, "Error looking up assessments")

        assessment = assessments[submission_uuid]
        return AssessmentSerializer(assessment).data
