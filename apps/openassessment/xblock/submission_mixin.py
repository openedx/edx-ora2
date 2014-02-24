from xblock.core import XBlock
from submissions import api


class SubmissionMixin(object):

    submit_errors = {
        # Reported to user sometimes, and useful in tests
        'ENOSUB':   'API submission is unrequested',
        'ENODATA':  'API returned an empty response',
        'EBADFORM': 'API Submission Request Error',
        'EUNKNOWN': 'API returned unclassified exception',
        'ENOMULTI': 'Multiple submissions are not allowed for this item',
    }

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """
        Place the submission text into Openassessment system
        """
        status = False
        status_tag = 'ENOSUB'
        status_text = None
        student_sub = data['submission']
        student_item_dict = self.get_student_item_dict()
        prev_sub = self._get_user_submission(student_item_dict)

        if prev_sub:
            # It is an error to submit multiple times for the same item
            status_tag = 'ENOMULTI'
        else:
            status_tag = 'ENODATA'
            try:
                response = api.create_submission(student_item_dict, student_sub)
            except api.SubmissionRequestError, e:
                status_tag = 'EBADFORM'
                status_text = unicode(e.field_errors)
            except api.SubmissionError:
                status_tag = 'EUNKNOWN'
            else:
                status = True
                status_tag = response.get('student_item')
                status_text = response.get('attempt_number')

        # relies on success being orthogonal to errors
        status_text = status_text if status_text else self.submit_errors[status_tag]
        return status, status_tag, status_text

    @staticmethod
    def _get_submission_score(student_item_dict, submission=False):
        """Return the most recent score, if any, for student item"""
        scores = False
        if submission:
            scores = api.get_score(student_item_dict)
        return scores[0] if scores else None

    @staticmethod
    def _get_user_submission(student_item_dict):
        """Return the most recent submission, if any, by user in student_item_dict"""
        submissions = []
        try:
            submissions = api.get_submissions(student_item_dict)
        except api.SubmissionRequestError:
            # This error is actually ok.
            pass
        return submissions[0] if submissions else None

    @XBlock.handler
    def render_submission(self, data, suffix=''):
        return self.render_assessment('static/html/oa_response.html')
