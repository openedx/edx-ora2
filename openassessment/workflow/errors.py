"""
Errors defined by the workflow API.
"""
from __future__ import absolute_import

import copy


class AssessmentWorkflowError(Exception):
    """An error that occurs during workflow actions.

    This error is raised when the Workflow API cannot perform a requested
    action.

    """


class AssessmentWorkflowInternalError(AssessmentWorkflowError):
    """An error internal to the Workflow API has occurred.

    This error is raised when an error occurs that is not caused by incorrect
    use of the API, but rather internal implementation of the underlying
    services.

    """


class AssessmentWorkflowRequestError(AssessmentWorkflowError):
    """This error is raised when there was a request-specific error

    This error is reserved for problems specific to the use of the API.

    """

    def __init__(self, field_errors):  # pylint: disable=super-init-not-called
        Exception.__init__(self, repr(field_errors))  # pylint: disable=non-parent-init-called
        self.field_errors = copy.deepcopy(field_errors)


class AssessmentWorkflowNotFoundError(AssessmentWorkflowError):
    """This error is raised when no submission is found for the request.

    If a state is specified in a call to the API that results in no matching
    Submissions, this error may be raised.

    """


class AssessmentApiLoadError(AssessmentWorkflowInternalError):
    """
    The assessment API could not be loaded.
    """
    def __init__(self, assessment_name, api_path):
        msg = u"Could not load assessment API for {} from {}".format(
            assessment_name, api_path
        )
        super(AssessmentApiLoadError, self).__init__(msg)
