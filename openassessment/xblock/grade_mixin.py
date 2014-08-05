"""
Grade step in the OpenAssessment XBlock.
"""
import copy
from collections import defaultdict
from lazy import lazy

from xblock.core import XBlock

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import ai as ai_api
from openassessment.assessment.errors import SelfAssessmentError, PeerAssessmentError
from submissions import api as sub_api
from openassessment.assessment.models import TrackChanges


class GradeMixin(object):
    """Grade Mixin introduces all handlers for displaying grades

    Abstracts all functionality and handlers associated with Grades.

    GradeMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    GradeMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_grade(self, data, suffix=''):
        """
        Render the grade step.

        Args:
            data: Not used.

        Keyword Arguments:
            suffix: Not used.

        Returns:
            unicode: HTML content of the grade step.
        """
        # Retrieve the status of the workflow.  If no workflows have been
        # started this will be an empty dict, so status will be None.
        workflow = self.get_workflow_info()
        status = workflow.get('status')

        # Default context is empty
        context = {}

        # Render the grading section based on the status of the workflow
        try:
            if status == "done":
                path, context = self.render_grade_complete(workflow)
            elif status == "waiting":
                path, context = self.render_grade_waiting(workflow)
            elif status is None:
                path = 'openassessmentblock/grade/oa_grade_not_started.html'
            else:  # status is 'self' or 'peer', which implies that the workflow is incomplete
                path, context = self.render_grade_incomplete(workflow)
        except (sub_api.SubmissionError, PeerAssessmentError, SelfAssessmentError):
            return self.render_error(self._(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def render_grade_waiting(self, workflow):
        """
        Render the grade waiting state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict) and template_path (string)

        """
        context = {
            "waiting": self.get_waiting_details(workflow["status_details"])
        }
        return 'openassessmentblock/grade/oa_grade_waiting.html', context

    def render_grade_complete(self, workflow):
        """
        Render the grade complete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """
        # Peer specific stuff...
        assessment_steps = self.assessment_steps
        submission_uuid = workflow['submission_uuid']

        example_based_assessment = None
        self_assessment = None
        feedback = None
        peer_assessments = []
        has_submitted_feedback = False

        if "peer-assessment" in assessment_steps:
            feedback = peer_api.get_assessment_feedback(submission_uuid)
            peer_assessments = [
                self._assessment_grade_context(asmnt)
                for asmnt in peer_api.get_assessments(submission_uuid)
            ]
            has_submitted_feedback = feedback is not None

        if "self-assessment" in assessment_steps:
            self_assessment = self._assessment_grade_context(
                self_api.get_assessment(submission_uuid)
            )

        if "example-based-assessment" in assessment_steps:
            example_based_assessment = self._assessment_grade_context(
                ai_api.get_latest_assessment(submission_uuid)
            )

        feedback_text = feedback.get('feedback', '') if feedback else ''
        student_submission = sub_api.get_submission(submission_uuid)

        # We retrieve the score from the workflow, which in turn retrieves
        # the score for our current submission UUID.
        # We look up the score by submission UUID instead of student item
        # to ensure that the score always matches the rubric.
        # It's possible for the score to be `None` even if the workflow status is "done"
        # when all the criteria in the rubric are feedback-only (no options).
        score = workflow['score']

        context = {
            'score': score,
            'feedback_text': feedback_text,
            'student_submission': student_submission,
            'peer_assessments': peer_assessments,
            'self_assessment': self_assessment,
            'example_based_assessment': example_based_assessment,
            'rubric_criteria': self._rubric_criteria_grade_context(peer_assessments, self_assessment),
            'has_submitted_feedback': has_submitted_feedback,
            'allow_file_upload': self.allow_file_upload,
            'allow_latex': self.allow_latex,
            'file_url': self.get_download_url_from_submission(student_submission)
        }

        # Update the scores we will display to the user
        # Note that we are updating a *copy* of the rubric criteria stored in
        # the XBlock field
        max_scores = peer_api.get_rubric_max_scores(submission_uuid)
        median_scores = None
        if "peer-assessment" in assessment_steps:
            median_scores = peer_api.get_assessment_median_scores(submission_uuid)
        elif "self-assessment" in assessment_steps:
            median_scores = self_api.get_assessment_scores_by_criteria(submission_uuid)
        elif "example-based-assessment" in assessment_steps:
            median_scores = ai_api.get_assessment_scores_by_criteria(submission_uuid)

        if median_scores is not None and max_scores is not None:
            for criterion in context["rubric_criteria"]:
                # Although we prevent course authors from modifying criteria post-release,
                # it's still possible for assessments created by course staff to
                # have criteria that differ from the current problem definition.
                # It's also possible to circumvent the post-release restriction
                # if course authors directly import a course into Studio.
                # If this happens, we simply leave the score blank so that the grade
                # section can render without error.
                criterion["median_score"] = median_scores.get(criterion["name"], '')
                criterion["total_value"] = max_scores.get(criterion["name"], '')

        return ('openassessmentblock/grade/oa_grade_complete.html', context)

    def render_grade_incomplete(self, workflow):
        """
        Render the grade incomplete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """
        def _is_incomplete(step):
            return (
                step in workflow["status_details"] and
                not workflow["status_details"][step]["complete"]
            )

        incomplete_steps = []
        if _is_incomplete("peer"):
            incomplete_steps.append(self._("Peer Assessment"))
        if _is_incomplete("self"):
            incomplete_steps.append(self._("Self Assessment"))

        return (
            'openassessmentblock/grade/oa_grade_incomplete.html',
            {'incomplete_steps': incomplete_steps}
        )

    @XBlock.json_handler
    def submit_feedback(self, data, suffix=''):
        """
        Submit feedback on an assessment.

        Args:
            data (dict): Can provide keys 'feedback_text' (unicode) and
                'feedback_options' (list of unicode).

        Keyword Arguments:
            suffix (str): Unused

        Returns:
            Dict with keys 'success' (bool) and 'msg' (unicode)

        """
        feedback_text = data.get('feedback_text', u'')
        feedback_options = data.get('feedback_options', list())

        try:
            peer_api.set_assessment_feedback({
                'submission_uuid': self.submission_uuid,
                'feedback_text': feedback_text,
                'options': feedback_options,
            })
        except (peer_api.PeerAssessmentInternalError, peer_api.PeerAssessmentRequestError):
            return {'success': False, 'msg': self._(u"Assessment feedback could not be saved.")}
        else:
            self.runtime.publish(
                self,
                "openassessmentblock.submit_feedback_on_assessments",
                {
                    'submission_uuid': self.submission_uuid,
                    'feedback_text': feedback_text,
                    'options': feedback_options,
                }
            )
            return {'success': True, 'msg': self._(u"Feedback saved.")}

    def _rubric_criteria_grade_context(self, peer_assessments, self_assessment):
        """
        Sanitize the rubric criteria into a format that can be passed
        into the grade complete Django template.

            * Add per-criterion feedback from peer assessments to the rubric criteria.
            * Filters out empty feedback.
            * Assign a "label" for criteria/options if none is defined (backwards compatibility).

        Args:
            peer_assessments (list of dict): Serialized assessment models from the peer API.
            self_assessment (dict): Serialized assessment model from the self API

        Returns:
            list of criterion dictionaries

        Example:
            [
                {
                    'label': 'Test name',
                    'name': 'f78ac7d4ca1e4134b0ba4b40ca212e72',
                    'prompt': 'Test prompt',
                    'order_num': 2,
                    'options': [...]
                    'feedback': [
                        'Good job!',
                        'Excellent work!',
                    ]
                },
                ...
            ]
        """
        criteria = copy.deepcopy(self.rubric_criteria_with_labels)
        peer_criteria_feedback = defaultdict(list)
        self_criteria_feedback = {}

        for assessment in peer_assessments:
            for part in assessment['parts']:
                if part['feedback']:
                    part_criterion_name = part['criterion']['name']
                    peer_criteria_feedback[part_criterion_name].append(part['feedback'])

        if self_assessment:
            for part in self_assessment['parts']:
                if part['feedback']:
                    part_criterion_name = part['criterion']['name']
                    self_criteria_feedback[part_criterion_name] = part['feedback']

        for criterion in criteria:
            criterion_name = criterion['name']
            criterion['peer_feedback'] = peer_criteria_feedback[criterion_name]
            criterion['self_feedback'] = self_criteria_feedback.get(criterion_name)

        return criteria

    @lazy
    def _criterion_and_option_labels(self):
        """
        Retrieve criteria and option labels from the rubric in the XBlock problem definition,
        defaulting to the name value if no label is available (backwards compatibility).

        Evaluated lazily, so it will return a cached value if called repeatedly.
        For the grade mixin, this should be okay, since we can't change the problem
        definition in the LMS (the settings fields are read-only).

        Returns:
            Tuple of dictionaries:
                `criterion_labels` maps criterion names to criterion labels.
                `option_labels` maps (criterion name, option name) tuples to option labels.

        """
        criterion_labels = {}
        option_labels = {}
        for criterion in self.rubric_criteria_with_labels:
            criterion_labels[criterion['name']] = criterion['label']
            for option in criterion['options']:
                option_label_key = (criterion['name'], option['name'])
                option_labels[option_label_key] = option['label']

        return criterion_labels, option_labels

    def _assessment_grade_context(self, assessment):
        """
        Sanitize an assessment dictionary into a format that can be
        passed into the grade complete Django template.

        Args:
            assessment (dict): The serialized assessment model.

        Returns:
            dict

        """
        assessment = copy.deepcopy(assessment)

        # Retrieve dictionaries mapping criteria/option names to the associated labels.
        # This is a lazy property, so we can call it repeatedly for each assessment.
        criterion_labels, option_labels = self._criterion_and_option_labels

        # Backwards compatibility: We used to treat "name" as both a user-facing label
        # and a unique identifier for criteria and options.
        # Now we treat "name" as a unique identifier, and we've added an additional "label"
        # field that we display to the user.
        # If criteria/options in the problem definition do NOT have a "label" field
        # (because they were created before this change),
        # we create a new label that has the same value as "name".
        for part in assessment['parts']:
            criterion_label_key = part['criterion']['name']
            part['criterion']['label'] = criterion_labels.get(criterion_label_key, part['criterion']['name'])

            # We need to be a little bit careful here: some assessment parts
            # have only written feedback, so they're not associated with any options.
            # If that's the case, we don't need to add the label field.
            if part.get('option') is not None:
                option_label_key = (part['criterion']['name'], part['option']['name'])
                part['option']['label'] = option_labels.get(option_label_key, part['option']['name'])

        assessment['track_changes'] = None
        track_changes = TrackChanges.objects.filter(scorer_id = assessment['scorer_id'],
                owner_submission_uuid = assessment['submission_uuid'])
        if track_changes:
            assessment['track_changes'] = track_changes.get().edited_content

        return assessment
