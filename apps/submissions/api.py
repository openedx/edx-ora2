"""
Public interface for the submissions app.

"""

def create_submission(student_item, answer, submitted_at=None):
    # score could be an optional param in the future.
    pass

def get_submissions(student_item, limit=None):
    pass

def get_score(student_item):
    pass

def get_scores(course_id, student_id, types=None):
    pass

def set_score(student_item):
    pass

