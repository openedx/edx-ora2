"""
The Staff Info View mixin renders all the staff-specific information used to
determine the flow of the problem.
"""
import copy
from django.utils.translation import ugettext as _

from xblock.core import XBlock
from openassessment.xblock.resolve_dates import DISTANT_PAST, DISTANT_FUTURE
from submissions import api as submission_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api


class StaffInfoMixin(object):

    @XBlock.handler
    def render_staff_info(self, data, suffix=''):
        """
        Template context dictionary for course staff debug panel.

        Returns:
            dict: The template context specific to the course staff debug panel.

        """
        # If we're not course staff, or in preview mode, return nothing for the
        # staff info view.
        if not self.is_course_staff or self.in_studio_preview:
            return self.render_error(_(
                u"You do not have permission to access staff information"
            ))
        student_item = self.get_student_item_dict()
        context = dict()
        path = 'openassessmentblock/staff_debug/staff_debug.html'

        # Calculate how many students are in each step of the workflow
        status_counts, num_submissions = self.get_workflow_status_counts()
        context['status_counts'] = status_counts
        context['num_submissions'] = num_submissions
        context['item_id'] = student_item["item_id"]

        # Include release/due dates for each step in the problem
        context['step_dates'] = list()

        steps = ['submission'] + self.assessment_steps
        for step in steps:

            # Get the dates as a student would see them
            __, __, start_date, due_date = self.is_closed(step=step, course_staff=False)

            context['step_dates'].append({
                'step': step,
                'start': start_date if start_date > DISTANT_PAST else None,
                'due': due_date if due_date < DISTANT_FUTURE else None,
            })

        return self.render_assessment(path, context)

    @XBlock.handler
    def render_student_info(self, data, suffix=''):
        """
        Renders all relative information for a specific student's workflow.

        Given a student's ID, we can render a staff-only section of the page
        with submissions and assessments specific to the student.

        Must be course staff to render this view.

        """
        # If request does not come from course staff, return nothing.
        # This should not be able to happen unless someone attempts to
        # explicitly invoke this handler.
        if not self.is_course_staff or self.in_studio_preview:
            return self.render_error(_(
                u"You do not have permission to access student information."
        ))

        path, context = self.get_student_info_path_and_context(data)
        return self.render_assessment(path, context)

    def get_student_info_path_and_context(self, data):
        """
        Get the proper path and context for rendering the the student info
        section of the staff debug panel.

        """
        student_id = data.params.get('student_id', '')
        submission_uuid = None
        submission = None
        assessment_steps = self.assessment_steps

        if student_id:
            student_item = self.get_student_item_dict()
            student_item['student_id'] = student_id

            # If there is a submission available for the requested student, present
            # it. If not, there will be no other information to collect.
            submissions = submission_api.get_submissions(student_item, 1)

            if submissions:
                submission = submissions[0]
                submission_uuid = submissions[0]['uuid']

        if "peer-assessment" in assessment_steps:
            peer_assessments = peer_api.get_assessments(submission_uuid)
            submitted_assessments = peer_api.get_submitted_assessments(submission_uuid, scored_only=False)
        else:
            peer_assessments = []
            submitted_assessments = []

        if "self-assessment" in assessment_steps:
            self_assessment = self_api.get_assessment(submission_uuid)
        else:
            self_assessment = None

        context = {
            'submission': submission,
            'peer_assessments': peer_assessments,
            'submitted_assessments': submitted_assessments,
            'self_assessment': self_assessment,
            'rubric_criteria': copy.deepcopy(self.rubric_criteria),
        }

        if peer_assessments or self_assessment:
            max_scores = peer_api.get_rubric_max_scores(submission_uuid)
            for criterion in context["rubric_criteria"]:
                criterion["total_value"] = max_scores[criterion["name"]]

        path = 'openassessmentblock/staff_debug/student_info.html'
        return path, context