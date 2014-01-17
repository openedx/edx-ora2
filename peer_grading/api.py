

def get_next_submission(student_id, location):
    """
    Request the next submission to be peer graded.
    Args:
        student_id(str): The student requesting to grade a peer. Must check to determine if the requesting student has
                         submitted an answer of their own.
        location(str): The associated location for the submission to be graded.
    Returns:
        Submission: The submission to grade, if one is available.
    """
    pass


def get_last_submission(student_id, location):
    """
    Used to give visibility to scoring and workflow for a submission in peer grading. If the student has submitted a
    submission and has graded enough peers, this function will return the submission as is, with all available scoring
    data. If the student has not finished grading peers, scoring information on their submission is withheld.
    Args:
        student_id (str): The student.
        location (str): The associated location.
    Returns:
        Submission: The student's latest submission, restrained on workflow completion.
    """
    pass


def submit_submission(submission):
    """
    Submit a submission for peer grading.
    Args:
        submission (Submission): The submission to add to the peer grading queue. Should contain the student_id,
                                 associated location, and all answer related fields prepopulated. Submission date,
                                 preferred grader, and other attributes can be determined internally.
    Returns:
        Submission: The saved submission.
    """
    pass


def submit_score(scoring, submission):
    """
    Submit a scoring for a particular submission
    Args:
        scoring (Scoring): The score for a particular submission.
        submission (Submission): The associated submission.
    Returns:
        bool: True if the submission succeeded.
    """
    pass
