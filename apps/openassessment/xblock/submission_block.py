from openassessment.xblock.assessment_block import AssessmentBlock
from submissions import api


class SubmissionBlock(AssessmentBlock):

    assessment_type = "submission"
    name = "submission"
    navigation_text = "Your response to this problem"
    path = "static/html/oa_response.html"
    title = "Your Response"

    submit_errors = {
        # Reported to user sometimes, and useful in tests
        'ENOSUB':   'API submission is unrequested',
        'ENODATA':  'API returned an empty response',
        'EBADFORM': 'API Submission Request Error',
        'EUNKNOWN': 'API returned unclassified exception',
    }

    def submit(self, student_item_dict, data):
        """
        Place the submission text into Openassessment system
        """
        status = False
        status_text = None
        student_sub = data['submission']
        try:
            status_tag = 'ENODATA'
            response = api.create_submission(student_item_dict, student_sub)
            if response:
                status = True
                status_tag = response.get('student_item')
                status_text = response.get('attempt_number')
        except api.SubmissionRequestError, e:
            status_tag = 'EBADFORM'
            status_text = unicode(e.field_errors)
        except api.SubmissionError:
            status_tag = 'EUNKNOWN'
            # relies on success being orthogonal to errors
        status_text = status_text if status_text else self.submit_errors[status_tag]
        return status, status_tag, status_text