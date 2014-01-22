from models import Submission


def get_submissions(submission):
    Submission.objects.filter(location_id=submission["location_id"],
                              student_id=submission["student_id"])


def create_submission(submission):
    Submission.objects.create(student_id=submission["student_id"],
                              location_id=submission["location_id"],
                              course_id=submission["course_id"],
                              essay_body=submission["essay_body"],
                              preferred_grading=submission["preferred_grading"]).save()


def update_submission():
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
