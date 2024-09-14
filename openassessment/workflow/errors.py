"""
Errors defined by the workflow API.
"""


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
        msg = "Could not load assessment API for {} from {}".format(
            assessment_name, api_path
        )
        super().__init__(msg)


class ItemNotFoundError(Exception):
    """An item was not found in the modulestore"""
    pass


class ExceptionWithContext(Exception):
    """An exception with optional context dict to be supplied in serialized result"""

    def __init__(self, context=None):
        super().__init__(self)
        self.context = context


class XBlockInternalError(ExceptionWithContext):
    """Errors from XBlock handlers"""

    def __str__(self):
        return str(self.context)
