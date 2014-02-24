from xblock.core import XBlock
from submissions import api


class SubmissionMixin(object):

    submit_errors = {
        # Reported to user sometimes, and useful in tests
        'ENOSUB':   'API submission is unrequested',
        'ENODATA':  'API returned an empty response',
        'EBADFORM': 'API Submission Request Error',
        'EUNKNOWN': 'API returned unclassified exception',
    }

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """
        Place the submission text into Openassessment system
        """
        student_item_dict = self.get_student_item_dict()
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

    @XBlock.handler
    def render_submission(self, data, suffix=''):
        return self.render_assessment('static/html/oa_response.html')
