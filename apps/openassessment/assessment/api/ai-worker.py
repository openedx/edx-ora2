"""
Public interface for AI training and grading, used by workers.
"""


def get_submission(grading_workflow_uuid):
    """
    Retrieve the submission associated with a particular grading workflow.

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.

    Returns:
        submission (JSON-serializable): submission from the student.

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def get_classifier_set(grading_workflow_uuid):
    """
    Retrieve the classifier set associated with a particular grading workflow.

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.

    Returns:
        dict: Maps criterion names to serialized classifiers.
            (binary classifiers are base-64 encoded).

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass



def create_assessment(grading_workflow_uuid, assessment):
    """
    Create an AI assessment (complete the AI grading task).

    Args:
        grading_workflow_uuid (str): The UUID of the grading workflow.
        assessment (dict): The serialized assessment.

    Returns:
        None

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def get_algorithm_id(training_workflow_uuid):
    """
    Retrieve the ID of the algorithm to use.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.

    Returns:
        unicode: The algorithm ID associated with the training task.

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    pass


def get_training_examples(training_workflow_uuid):
    """
    Retrieve the training examples associated with a training task.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.

    Returns:
        list of dict: Serialized training examples.

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    pass


def create_classifiers(training_workflow_uuid, classifier_set):
    """
    Upload trained classifiers and mark the workflow complete.

    If grading tasks were submitted before any classifiers were trained,
    this call will automatically reschedule those tasks.

    Args:
        training_workflow_uuid (str): The UUID of the training workflow.
        classifier_set (dict): Mapping of criterion names to serialized classifiers.
            (binary classifiers should be base-64 encoded).

    Returns:
        None

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    pass
