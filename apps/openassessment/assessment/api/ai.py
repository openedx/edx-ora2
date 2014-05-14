"""
Public interface for AI training and grading, used by students/course authors.
"""


def submit(submission_uuid, rubric):
    """
    Submit a response for AI assessment.
    This will:
        (a) create a workflow (database record) to track the grading task
        (b) if classifiers exist for the rubric, schedule an asynchronous grading task.

    Args:
        submission_uuid (str): The UUID of the submission to assess.
        rubric (dict): Serialized rubric model.

    Returns:
        grading_workflow_uuid (str): The UUID of the grading workflow.
            Usually the caller of `submit()` won't need this (since the workers
            are parameterized by grading workflow UUID), but it's
            useful for testing.

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def get_latest_assessment(submission_uuid):
    """
    Retrieve the latest AI assessment for a submission.

    Args:
        submission_uuid (str): The UUID of the submission being assessed.

    Returns:
        dict: The serialized assessment model

    Raises:
        AIGradingRequestError
        AIGradingInternalError

    """
    pass


def train_classifiers(rubric, examples, algorithm_id):
    """
    Schedule a task to train classifiers.
    All training examples must match the rubric!

    Args:
        rubric (dict): The rubric used to assess the classifiers.
        examples (list of dict): Serialized training examples.
        algorithm_id (unicode): The ID of the algorithm used to train the classifiers.

    Returns:
        training_workflow_uuid (str): The UUID of the training workflow.
            Usually the caller will not need this (since the workers
            are parametrized by training workflow UUID), but it's
            useful for testing.

    Raises:
        AITrainingRequestError
        AITrainingInternalError

    """
    pass


def reschedule_unfinished_tasks(course_id=None, item_id=None, task_type=None):
    """
    Check for unfinished tasks (both grading and training) and reschedule them.
    Optionally restrict by course/item ID and task type.

    Kwargs:
        course_id (unicode): Restrict to unfinished tasks in a particular course.
        item_id (unicode): Restrict to unfinished tasks for a particular item in a course.
            NOTE: if you specify the item ID, you must also specify the course ID.
        task_type (unicode): Either "grade" or "train".  Restrict to unfinished tasks of this type.

    Raises:
        AIRequestError
        AIInternalError

    """
    pass
