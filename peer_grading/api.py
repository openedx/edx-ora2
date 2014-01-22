from common_grading.models import GRADING_TYPES
import common_grading.data_service as data_service


def get_next_submission(submission):
    """Request the next submission to be peer graded.

    Args:
        student_id (str): The student requesting to grade a peer. Must check to determine if the requesting student has
            submitted an answer of their own.
        location (str): The associated location for the submission to be graded.
    Returns:
        Submission: The submission to grade, if one is available.

    """
    pass


def get_submission(submission):
    """Used to give visibility to scoring and workflow for a submission in peer grading.

    If the student has submitted a submission and has graded enough peers, this function will return the submission as
    is, with all available scoring data. If the student has not finished grading peers, scoring information on their
    submission is withheld.

    Args:
        student_id (str): The student.
        location (str): The associated location.
    Returns:
        Submission: The student's latest submission, restrained on workflow completion.

    """
    return data_service.get_submissions(submission)


def create_submission(submission):
    """Submit a submission for peer grading.

    Args:
        student_id (str): The submitting student.
        location (str): The location this submission is associated with.
        course_id (str): The course this submission is associated with.
        essay_body (str): The body of the submission to grade.
    Returns:
        Submission: The saved submission.
    """
    submission["preferred_grading"] = GRADING_TYPES[0]
    data_service.create_submission(submission)


def update_submission(submission):
    """Submit a scoring for a particular submission

    Args:
        scoring (Scoring): The score for a particular submission.
        submission (Submission): The associated submission.
    Returns:
        bool: True if the submission succeeded.

    """
    pass


def get_scoring():
    pass


def create_scoring():
    pass


def update_scoring():
    pass


def get_feedback():
    pass


def create_feedback():
    pass


def update_feedback():
    pass