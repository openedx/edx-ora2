"""
Workflow related methods.

The only weird thing here would be that the XBlock needs to pass in a lot of
information about problem constraints. This could happen at either query time
or we could have it trigger on save in the studio/authoring view (though that
might be tricky with XML import based courses).

(There would be a lot more here.)

"""

def create_evaluation(submission_id, score, rubric):
    pass

def get_submission_to_evaluate(student_item, scorer_student_id):
    pass
