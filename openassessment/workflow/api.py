"""
Public interface for the Assessment Workflow.

"""
import logging

from django.db import DatabaseError

from submissions import api as sub_api
from openassessment.assessment.errors import PeerAssessmentError, PeerAssessmentInternalError

from .errors import (AssessmentWorkflowError, AssessmentWorkflowInternalError, AssessmentWorkflowNotFoundError,
                     AssessmentWorkflowRequestError)
from .models import AssessmentWorkflow, AssessmentWorkflowCancellation
from .serializers import AssessmentWorkflowCancellationSerializer, AssessmentWorkflowSerializer

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def create_workflow(submission_uuid, steps, on_init_params=None):
    """Begins a new assessment workflow.

    Create a new workflow that other assessments will record themselves against.

    Args:
        submission_uuid (str): The UUID for the submission that all our
            assessments will be evaluating.
        steps (list): List of steps that are part of the workflow, in the order
            that the user must complete them. Example: `["peer", "self"]`

    Keyword Arguments:
        on_init_params (dict): The parameters to pass to each assessment module
            on init.  Keys are the assessment step names.

    Returns:
        dict: Assessment workflow information with the following
            `uuid` = UUID of this `AssessmentWorkflow`
            `submission_uuid` = UUID of submission this workflow tracks
            `status` = Active step, always "peer" when created.
            `created` = created datetime
            'modified' = modified datetime (same as `created` for this method)
            'score' = should be None in the usual case, but could be a dict
                with keys "points_earned" and "points_possible` and int values.
                The latter will only happen on workflow creation if something
                else has already written the score for this submission (such as
                a professor manually entering it). There is no support for such
                a feature at present, but it may be added later.

    Raises:
        AssessmentWorkflowRequestError: If the `submission_uuid` passed in does
            not exist or is of an invalid type.
        AssessmentWorkflowInternalError: Unexpected internal error, such as the
            submissions app not being available or a database configuration
            problem.

    """
    def sub_err_msg(specific_err_msg):
        """ Submission error message"""
        return (
            "Could not create assessment workflow: "
            "retrieving submission {} failed: {}"
            .format(submission_uuid, specific_err_msg)
        )

    if on_init_params is None:
        on_init_params = {}

    try:
        workflow = AssessmentWorkflow.start_workflow(submission_uuid, steps, on_init_params)
        logger.info(
            "Started assessment workflow for submission UUID %s with steps %s",
            submission_uuid,
            steps
        )
        return AssessmentWorkflowSerializer(workflow).data
    except sub_api.SubmissionNotFoundError as ex:
        err_msg = sub_err_msg("submission not found")
        logger.error(err_msg)
        raise AssessmentWorkflowRequestError(err_msg) from ex
    except sub_api.SubmissionRequestError as err:
        err_msg = sub_err_msg(err)
        logger.error(err_msg)
        raise AssessmentWorkflowRequestError(err_msg) from err
    except sub_api.SubmissionInternalError as err:
        logger.error(err)
        raise AssessmentWorkflowInternalError(
            "retrieving submission {} failed with unknown error: {}"
            .format(submission_uuid, err)
        ) from err
    except DatabaseError as ex:
        err_msg = f"Could not create assessment workflow for submission UUID: {submission_uuid}"
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from ex
    except Exception as ex:
        err_msg = (
            "An unexpected error occurred while creating "
            "the workflow for submission UUID {}"
        ).format(submission_uuid)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from ex


def get_workflow_for_submission(submission_uuid, assessment_requirements, course_settings):
    """Returns Assessment Workflow information

    This will implicitly call `update_from_assessments()` to make sure we
    give the most current information. Unlike `create_workflow()`, this function
    will check our assessment sequences to see if they are complete. We pass
    in the `assessment_requirements` each time we make the request because the
    canonical requirements are stored in the `OpenAssessmentBlock` problem
    definition and may change over time.

    Args:
        submission_uuid (str): Identifier for the submission the
            `AssessmentWorkflow` was created to track. There is a 1:1
            relationship between submissions and workflows, so this uniquely
            identifies the `AssessmentWorkflow`.
        assessment_requirements (dict): Dictionary that currently looks like:
            `{"peer": {"must_grade": <int>, "must_be_graded_by": <int>}}`
            `must_grade` is the number of assessments a student must complete.
            `must_be_graded_by` is the number of assessments a submission must
            receive to be scored. `must_grade` should be greater than
            `must_be_graded_by` to ensure that everyone will get scored.
            The intention is to eventually pass in more assessment sequence
            specific requirements in this dict.

    Returns:
        dict: Assessment workflow information with the following
            `uuid` = UUID of this `AssessmentWorkflow`
            `submission_uuid` = UUID of submission this workflow tracks
            `status` = Active step, always "peer" when created.
            `created` = created datetime
            'modified' = modified datetime (same as `created` for this method)
            'score' = None if no score is present. A dict with keys
                `points_earned` and `points_possible` and int values if a score
                has been created for this submission. We only do this when we
                mark a workflow `done`, but it is possible that other processes
                will later manually write that score information.
            `status_details` = dict with the keys `peer` and `self`, each of
                which has a dict with a key of `complete` and a boolean value.
                The intention is to tell you the completion status of each
                assessment sequence, but we will likely use this for extra
                information later on.

    Raises:
        AssessmentWorkflowRequestError: If the `workflow_uuid` passed in is not
            a string type.
        AssessmentWorkflowNotFoundError: No assessment workflow matching the
            requested UUID exists.
        AssessmentWorkflowInternalError: Unexpected internal error, such as the
            submissions app not being available or a database configuation
            problem.

    Examples:
        >>> get_workflow_for_submission(
        ...     '222bdf3d-a88e-11e3-859e-040ccee02800',
        ...     {"peer": {"must_grade":5, "must_be_graded_by":3}}
        ... )
        ...
        {
            'uuid': u'53f27ecc-a88e-11e3-8543-040ccee02800',
            'submission_uuid': u'222bdf3d-a88e-11e3-859e-040ccee02800',
            'status': u'peer',
            'created': datetime.datetime(2014, 3, 10, 19, 58, 19, 846684, tzinfo=<UTC>),
            'modified': datetime.datetime(2014, 3, 10, 19, 58, 19, 846957, tzinfo=<UTC>),
            'score': None,
            'status_details': {
                'peer': {
                    'complete': False
                },
                'self': {
                    'complete': False
                }
            }
        }

    """
    return update_from_assessments(submission_uuid, assessment_requirements, course_settings)


def update_from_assessments(
    submission_uuid,
    assessment_requirements,
    course_settings,
    override_submitter_requirements=False
):
    """
    Update our workflow status based on the status of the underlying assessments.

    We pass in the `assessment_requirements` each time we make the request
    because the canonical requirements are stored in the `OpenAssessmentBlock`
    problem definition and may change over time. Because this method also
    returns a copy of the `WorkflowAssessment` information as a convenience,
    it's functionally equivalent to calling `get_workflow_for_submission()`.
    This is a little wonky from a REST, get-doesn't-change-state point of view,
    except that what's stored in the `AssessmentWorkflow` isn't the canonical
    true value -- it's just the most recently known state of it based on the
    last known requirments. For now, we have to query for truth.

    Args:
        submission_uuid (str): Identifier for the submission the
            `AssessmentWorkflow` was created to track. There is a 1:1
            relationship between submissions and workflows, so this uniquely
            identifies the `AssessmentWorkflow`.
        assessment_requirements (dict): Dictionary that currently looks like:
            `{"peer": {
                 "must_grade": <int>,
                 "must_be_graded_by": <int>,
                 "enable_flexible_grading": <bool>
            }}`
            `must_grade` is the number of assessments a student must complete.
            `must_be_graded_by` is the number of assessments a submission must
            receive to be scored. `must_grade` should be greater than
            `must_be_graded_by` to ensure that everyone will get scored.
            `enable_flexible_grading` loosens the number of required peer
            assessments to `floor(0.7 * must_be_graded_by)` in case the
            submission is more than 7 days old
            The intention is to eventually pass in more assessment sequence
            specific requirements in this dict.
        override_submitter_requirements (bool): If True, the presence of a new
            staff score will cause all of the submitter's requirements to be
            fulfilled, moving the workflow to DONE and exposing their grade.

    Returns:
        dict: Assessment workflow information with the following
            `uuid` = UUID of this `AssessmentWorkflow`
            `submission_uuid` = UUID of submission this workflow tracks
            `status` = Active step, always "peer" when created.
            `created` = created datetime
            'modified' = modified datetime (same as `created` for this method)
            'score' = None if no score is present. A dict with keys
                `points_earned` and `points_possible` and int values if a score
                has been created for this submission. We only do this when we
                mark a workflow `done`, but it is possible that other processes
                will later manually write that score information.
            `status_details` = dict with the keys `peer` and `self`, each of
                which has a dict with a key of `complete` and a boolean value.
                The intention is to tell you the completion status of each
                assessment sequence, but we will likely use this for extra
                information later on.

    Raises:
        AssessmentWorkflowRequestError: If the `workflow_uuid` passed in is not
            a string type.
        AssessmentWorkflowNotFoundError: No assessment workflow matching the
            requested UUID exists.
        AssessmentWorkflowInternalError: Unexpected internal error, such as the
            submissions app not being available or a database configuation
            problem.

    Examples:
        >>> update_from_assessments(
        ...     '222bdf3d-a88e-11e3-859e-040ccee02800',
        ...     {"peer": {"must_grade":5, "must_be_graded_by":3}}
        ... )
        ...
        {
            'uuid': u'53f27ecc-a88e-11e3-8543-040ccee02800',
            'submission_uuid': u'222bdf3d-a88e-11e3-859e-040ccee02800',
            'status': u'peer',
            'created': datetime.datetime(2014, 3, 10, 19, 58, 19, 846684, tzinfo=<UTC>),
            'modified': datetime.datetime(2014, 3, 10, 19, 58, 19, 846957, tzinfo=<UTC>),
            'score': None,
            'status_details': {
                'peer': {
                    'complete': False
                },
                'self': {
                    'complete': False
                }
            }
        }

    """
    workflow = _get_workflow_model(submission_uuid)

    try:
        workflow.update_from_assessments(
            assessment_requirements,
            course_settings,
            override_submitter_requirements
        )
        logger.info(
            "Updated workflow for submission UUID %s with requirements %s and course setttings %s",
            submission_uuid,
            assessment_requirements,
            course_settings
        )
        return _serialized_with_details(workflow)
    except PeerAssessmentError as err:
        err_msg = "Could not update assessment workflow: %s"
        logger.exception(err_msg, err)
        raise AssessmentWorkflowInternalError(err_msg % err) from err


def get_status_counts(course_id, item_id, steps):
    """
    Count how many workflows have each status, for a given item in a course.

    Keyword Arguments:
        course_id (unicode): The ID of the course.
        item_id (unicode): The ID of the item in the course.
        steps (list): A list of assessment steps for this problem.

    Returns:
        list of dictionaries with keys "status" (str) and "count" (int)

    Example usage:
        >>> get_status_counts("ora2/1/1", "peer-assessment-problem", ["peer"])
        [
            {"status": "peer", "count": 5},
            {"status": "self", "count": 10},
            {"status": "waiting", "count": 43},
            {"status": "done", "count": 12},
        ]

    """
    # The AI status exists for workflow logic, but no student will ever be in
    # the AI status, so we should never return it.
    statuses = steps + AssessmentWorkflow.STATUSES
    if 'ai' in statuses:
        statuses.remove('ai')
    return [
        {
            "status": status,
            "count": AssessmentWorkflow.objects.filter(
                status=status,
                course_id=course_id,
                item_id=item_id,
            ).count()
        }
        for status in statuses
    ]


def _get_workflow_model(submission_uuid):
    """Return the `AssessmentWorkflow` model for a given `submission_uuid`.

    This method will raise the appropriate `AssessmentWorkflowError` while
    trying to fetch the model object. This method assumes the object already
    exists and will not attempt to create one.

    Args:
        submission_uuid (str): Identifier for the submission the
            `AssessmentWorkflow` was created to track. There is a 1:1
            relationship between submissions and workflows, so this uniquely
            identifies the `AssessmentWorkflow`.

    Returns:
        `AssessmentWorkflow`: The workflow used to track the global progress of
            this submission as it works its way through the peer and self
            assessment sequences.

    Raises:
        AssessmentWorkflowRequestError: If the `workflow_uuid` passed in is not
            a string type.
        AssessmentWorkflowNotFoundError: No assessment workflow matching the
            requested UUID exists.
        AssessmentWorkflowInternalError: Unexpected internal error, such as the
            submissions app not being available or a database configuation
            problem.

    """
    if not isinstance(submission_uuid, str):
        raise AssessmentWorkflowRequestError("submission_uuid must be a string type")

    try:
        workflow = AssessmentWorkflow.get_by_submission_uuid(submission_uuid)
    except AssessmentWorkflowError as exc:
        raise AssessmentWorkflowInternalError(repr(exc)) from exc
    except Exception as exc:
        # Something very unexpected has just happened (like DB misconfig)
        err_msg = (
            "Could not get assessment workflow with submission_uuid {} due to error: {}"
            .format(submission_uuid, exc)
        )
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg) from exc

    if workflow is None:
        raise AssessmentWorkflowNotFoundError(
            f"No assessment workflow matching submission_uuid {submission_uuid}"
        )

    return workflow


def _serialized_with_details(workflow):
    """
    Given a workflow, return its serialized version with added status details.
    """
    data_dict = AssessmentWorkflowSerializer(workflow).data
    data_dict["status_details"] = workflow.status_details()
    return data_dict


def cancel_workflow(submission_uuid, comments, cancelled_by_id, assessment_requirements, course_settings):
    """
    Add an entry in AssessmentWorkflowCancellation table for a AssessmentWorkflow.

    AssessmentWorkflow which has been cancelled is no longer included in the
    peer grading pool.

    Args:
        submission_uuid (str): The UUID of the workflow's submission.
        comments (str): The reason for cancellation.
        cancelled_by_id (str): The ID of the user who cancelled the peer workflow.
        assessment_requirements (dict): Dictionary that currently looks like:
            `{"peer": {"must_grade": <int>, "must_be_graded_by": <int>}}`
            `must_grade` is the number of assessments a student must complete.
            `must_be_graded_by` is the number of assessments a submission must
            receive to be scored. `must_grade` should be greater than
            `must_be_graded_by` to ensure that everyone will get scored.
            The intention is to eventually pass in more assessment sequence
            specific requirements in this dict.
        course_settings (dict): Dictionary that contains course-level settings that
                                impact workflow steps
    """
    AssessmentWorkflow.cancel_workflow(
        submission_uuid,
        comments, cancelled_by_id,
        assessment_requirements,
        course_settings
    )


def get_assessment_workflow_cancellation(submission_uuid):
    """
    Get cancellation information for an assessment workflow.

    Args:
        submission_uuid (str): The UUID of the submission.
    """
    try:
        workflow_cancellation = AssessmentWorkflowCancellation.get_latest_workflow_cancellation(submission_uuid)
        return AssessmentWorkflowCancellationSerializer(workflow_cancellation).data if workflow_cancellation else None
    except DatabaseError as ex:
        error_message = "Error finding assessment workflow cancellation for submission UUID {}."\
            .format(submission_uuid)
        logger.exception(error_message)
        raise PeerAssessmentInternalError(error_message) from ex


def is_workflow_cancelled(submission_uuid):
    """
    Check if assessment workflow is cancelled?

    Args:
        submission_uuid (str): The UUID of the assessment workflow.

    Returns:
        True/False
    """
    try:
        workflow = AssessmentWorkflow.get_by_submission_uuid(submission_uuid)
        return workflow.is_cancelled if workflow else False
    except AssessmentWorkflowError:
        return False


def get_workflows_for_status(course_id, item_id, status_list):
    """
    Retrieves workflow data for all workflows

    Args:
        course_id (str): The course that this problem belongs to.
        item_id (str): The student_item (problem) that we want to know statistics about.
        status_list (list(str)): a list of status to retrieve workflows for

    Returns:
        list of dictionaries with `submission_id` and `status`
    """
    workflows = AssessmentWorkflow.objects.filter(
        course_id=course_id,
        item_id=item_id,
        status__in=status_list
    )
    return [
        {
            "submission_uuid": workflow.submission_uuid,
            "status": workflow.status
        }
        for workflow in workflows
    ]
