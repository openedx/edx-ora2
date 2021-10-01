"""
API endpoints for enhanced staff grader
"""

from django.db.models import Case, OuterRef, Prefetch, Subquery, Value, When
from django.db.models.fields import CharField
from submissions.api import get_student_ids_by_submission_uuid
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError

from openassessment.assessment.models.base import Assessment, AssessmentPart
from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.data import map_anonymized_ids_to_usernames
from openassessment.staffgrader.errors.submission_lock import SubmissionLockContestedError
from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.staffgrader.serializers.submission_lock import SubmissionLockSerializer
from openassessment.xblock.staff_area_mixin import require_course_staff


class StaffGraderMixin:
    """
    Actions to interact with submission locks, blocking other staff from grading assignments while
    grading is in progress.
    """

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def check_submission_lock(self, data, suffix=""):  # pylint: disable=unused-argument
        # Unpack / validate request
        submission_uuid = data.get('submission_id', None)
        if not submission_uuid:
            raise JsonHandlerError(400, "Body must contain a submission_id")

        submission_lock = SubmissionGradingLock.get_submission_lock(submission_uuid)

        if submission_lock:
            return SubmissionLockSerializer(submission_lock).data
        else:
            return {}

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def claim_submission_lock(self, data, suffix=''):  # pylint: disable=unused-argument
        # Unpack / validate request
        submission_uuid = data.get('submission_id', None)
        if not submission_uuid:
            raise JsonHandlerError(400, "Body must contain a submission_id")
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()

        try:
            submission_lock = SubmissionGradingLock.claim_submission_lock(submission_uuid, anonymous_user_id)
            return SubmissionLockSerializer(submission_lock).data
        except SubmissionLockContestedError as err:
            raise JsonHandlerError(403, str(err)) from err

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def delete_submission_lock(self, data, suffix=''):  # pylint: disable=unused-argument
        # Unpack / validate request
        submission_uuid = data.get('submission_id', None)
        if not submission_uuid:
            raise JsonHandlerError(400, "Body must contain a submission_id")
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()

        try:
            SubmissionGradingLock.clear_submission_lock(submission_uuid, anonymous_user_id)
            return {}
        except SubmissionLockContestedError as err:
            raise JsonHandlerError(403, str(err)) from err

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
        # Return seriaized staff workflows with additional Assessment / User / Team data.
        # This is primarily split off in case we want to add pagination to this handler.
        return self.staff_workflows_to_api_format(staff_workflows)

    def staff_workflows_to_api_format(self, staff_workflows):
        """
        Fetch additional required data and models, and serialize staff workflows
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
        # if not self.is_team_assignment():
        # When we look up usernames we want to include all connected learner student ids
        submission_uuids_to_student_id = get_student_ids_by_submission_uuid(
            course_id,
            submission_uuids,
        )
        # else:
        #     # Team assignments don't need individual username lookups but do look up team ids and
        #     # then map team IDs to team names.
        #     submission_uuids_to_student_id = dict()
        #     submission_uuids_to_team_id = get_team_ids_by_team_submission_uuid(submission_uuids)
        #     submission_uuids_to_team_name = {
        #         submission_uuid: self.teams_service.get_team_by_team_id(team_id)
        #         for submission_uuid, team_id in submission_uuids_to_team_id.items()
        #     }

        # Do bulk lookup for all anonymous ids. This is used for team + individual for
        # looking up username of "scorer", and to provide "username" for individual
        # assignments
        anonymous_ids_to_usernames = map_anonymized_ids_to_usernames(
            set(submission_uuids_to_student_id.values()) | workflow_scorer_ids
        )

        # Do a bulk fetch of the assessments linked to the workflows, including all connected
        # Rubric, Criteria, and Option models
        assessments_by_submission_uuid = self.bulk_deep_fetch_assessments(assessment_ids)

        response = {}
        for workflow in staff_workflows:
            workflow_dict = {
                "submission_uuid": workflow.submission_uuid,
                "dateSubmitted": str(workflow.created_at),
                "dateGraded": str(workflow.grading_completed_at),
                "gradingStatus": workflow.grading_status,
                "lockStatus": workflow.lock_status,
            }

            if workflow.scorer_id:
                workflow_dict["gradedBy"] = anonymous_ids_to_usernames[workflow.scorer_id]
            else:
                workflow_dict['gradedBy'] = ''

            # if self.is_team_assignment():
            #     # workflow_dict['team_name'] = submission_uuids_to_team_name[workflow.identifying_uuid]
            # else:
            student_id = submission_uuids_to_student_id[workflow.identifying_uuid]
            workflow_dict['username'] = anonymous_ids_to_usernames[student_id]

            assessment = assessments_by_submission_uuid.get(workflow.identifying_uuid)
            if assessment:
                workflow_dict['score'] = {
                    'points_earned': assessment.points_earned,
                    'points_possible': assessment.points_possible,
                }
            else:
                workflow_dict['score'] = dict()

            response[workflow.submission_uuid] = workflow_dict

        return response

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
