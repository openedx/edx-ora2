"""
Public interface for the Assessment Workflow.

"""
import copy
import logging

from django.db import DatabaseError

from openassessment.assessment import peer_api
from submissions import api as sub_api
from .models import AssessmentWorkflow
from .serializers import AssessmentWorkflowSerializer

logger = logging.getLogger(__name__)


class AssessmentWorkflowError(Exception):
    """An error that occurs during workflow actions.

    This error is raised when the Workflow API cannot perform a requested
    action.

    """
    pass


class AssessmentWorkflowInternalError(AssessmentWorkflowError):
    """An error internal to the Workflow API has occurred.

    This error is raised when an error occurs that is not caused by incorrect
    use of the API, but rather internal implementation of the underlying
    services.

    """
    pass


class AssessmentWorkflowRequestError(AssessmentWorkflowError):
    """This error is raised when there was a request-specific error

    This error is reserved for problems specific to the use of the API.

    """

    def __init__(self, field_errors):
        Exception.__init__(self, repr(field_errors))
        self.field_errors = copy.deepcopy(field_errors)


class AssessmentWorkflowNotFoundError(AssessmentWorkflowError):
    """This error is raised when no submission is found for the request.

    If a state is specified in a call to the API that results in no matching
    Submissions, this error may be raised.

    """
    pass


def create_workflow(submission_uuid):
    """Begins a new assessment workflow.

    Create a new workflow that other assessments will record themselves against.

    Args:
        submission_uuid (str): The UUID for the submission that all our
            assessments will be evaluating.

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
            submissions app not being available or a database configuation
            problem.

    """
    def sub_err_msg(specific_err_msg):
        return (
            u"Could not create assessment workflow: "
            u"retrieving submission {} failed: {}"
            .format(submission_uuid, specific_err_msg)
        )

    try:
        submission_dict = sub_api.get_submission(submission_uuid)
    except sub_api.SubmissionNotFoundError as err:
        err_msg = sub_err_msg("submission not found")
        logger.error(err_msg)
        raise AssessmentWorkflowRequestError(err_msg)
    except sub_api.SubmissionRequestError as err:
        err_msg = sub_err_msg(err)
        logger.error(err_msg)
        raise AssessmentWorkflowRequestError(err_msg)
    except sub_api.SubmissionInternalError as err:
        err_msg = sub_err_msg(err)
        logger.error(err)
        raise AssessmentWorkflowInternalError(
            u"retrieving submission {} failed with unknown error: {}"
            .format(submission_uuid, err)
        )

    # We're not using a serializer to deserialize this because the only variable
    # we're getting from the outside is the submission_uuid, which is already
    # validated by this point.
    try:
        peer_api.create_peer_workflow(submission_uuid)
        workflow = AssessmentWorkflow.objects.create(
            submission_uuid=submission_uuid,
            status=AssessmentWorkflow.STATUS.peer
        )
    except (DatabaseError, peer_api.PeerAssessmentError) as err:
        err_msg = u"Could not create assessment workflow: {}".format(err)
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg)

    return AssessmentWorkflowSerializer(workflow).data


def get_workflow_for_submission(submission_uuid, assessment_requirements):
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
    return update_from_assessments(submission_uuid, assessment_requirements)


def update_from_assessments(submission_uuid, assessment_requirements):
    """Update our workflow status based on the status of peer and self assessments.

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
    workflow = _get_workflow_model(submission_uuid)
    workflow.update_from_assessments(assessment_requirements)
    return _serialized_with_details(workflow, assessment_requirements)


def get_status_counts(**kwargs):
    """
    Count how many workflows have each status, for a given item in a course.

    Kwargs:
        course_id (unicode): The ID of the course.
        item_id (unicode): The ID of the item in the course.
        item_type (unicode): The type of the item.

    Returns:
        list of dictionaries with keys "status" (str) and "count" (int)

    Example usage:
        >>> get_status_counts("ora2/1/1", "peer-assessment-problem")
        [
            {"status": "peer", "count": 5},
            {"status": "self", "count": 10},
            {"status": "waiting", "count": 43},
            {"status": "done", "count": 12},
        ]

    """
    submission_uuids = sub_api.get_submission_uuids(**kwargs)
    workflows = AssessmentWorkflow.objects.filter(submission_uuid__in=submission_uuids)
    return [
        {"status": status, "count": workflows.filter(status=status).count()}
        for status in AssessmentWorkflow.STATUS_VALUES
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
    if not isinstance(submission_uuid, basestring):
        raise AssessmentWorkflowRequestError("submission_uuid must be a string type")

    try:
        workflow = AssessmentWorkflow.objects.get(submission_uuid=submission_uuid)
    except AssessmentWorkflow.DoesNotExist:
        raise AssessmentWorkflowNotFoundError(
            u"No assessment workflow matching submission_uuid {}".format(submission_uuid)
        )
    except Exception as exc:
        # Something very unexpected has just happened (like DB misconfig)
        err_msg = (
            "Could not get assessment workflow with submission_uuid {} due to error: {}"
            .format(submission_uuid, exc)
        )
        logger.exception(err_msg)
        raise AssessmentWorkflowInternalError(err_msg)

    return workflow

def _serialized_with_details(workflow, assessment_requirements):
    """Given a workflow and assessment requirements, return the serialized
    version of an `AssessmentWorkflow` and add in the status details. See
    `update_from_assessments()` for details on params and return values.
    """
    data_dict = AssessmentWorkflowSerializer(workflow).data
    data_dict["status_details"] = workflow.status_details(assessment_requirements)
    return data_dict

