"""
Grade step in the OpenAssessment XBlock.
"""


import copy

from lazy import lazy
from xblock.core import XBlock

from django.utils.translation import gettext as _

from openassessment.assessment.errors import PeerAssessmentError, SelfAssessmentError

from .data_conversion import create_submission_dict


class GradeMixin:
    """Grade Mixin introduces all handlers for displaying grades

    Abstracts all functionality and handlers associated with Grades.

    GradeMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    GradeMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_grade(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Render the grade step.

        Args:
            data: Not used.

        Keyword Arguments:
            suffix: Not used.

        Returns:
            unicode: HTML content of the grade step.
        """
        # Import is placed here to avoid model import at project startup.
        from submissions import api as sub_api

        # Retrieve the status of the workflow.  If no workflows have been
        # started this will be an empty dict, so status will be None.
        workflow = self.get_workflow_info()
        status = workflow.get('status')

        # Default context is empty
        context = {'xblock_id': self.get_xblock_id()}

        assessment_steps = self.assessment_steps
        # Render the grading section based on the status of the workflow
        try:
            if status == "cancelled":
                path = 'openassessmentblock/grade/oa_grade_cancelled.html'
                context['score'] = workflow['score']
            elif status == "done":
                path, context = self.render_grade_complete(workflow)
            elif status == "waiting":
                # The class "is--waiting--staff" is needed in the grade template for the javascript to
                # send focus to the correct step.
                # In the case where the user has completed all steps but is still waiting on a staff grade,
                # we want focus to go from the assessment steps to the staff grading step.
                if "staff-assessment" in assessment_steps:
                    context['is_waiting_staff'] = "is--waiting--staff"
                context['score_explanation'] = self._get_score_explanation(workflow)

                path = 'openassessmentblock/grade/oa_grade_waiting.html'
            elif status is None:
                path = 'openassessmentblock/grade/oa_grade_not_started.html'
            else:  # status is 'self' or 'peer', which implies that the workflow is incomplete
                path, context = self.render_grade_incomplete(workflow)
        except (sub_api.SubmissionError, PeerAssessmentError, SelfAssessmentError):
            return self.render_error(self._("An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def render_grade_complete(self, workflow):
        """
        Render the grade complete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """
        # Import is placed here to avoid model import at project startup.
        from submissions import api as sub_api

        from openassessment.assessment.api import peer as peer_api
        from openassessment.assessment.api import self as self_api
        from openassessment.assessment.api import staff as staff_api

        # Peer specific stuff...
        assessment_steps = self.assessment_steps
        submission_uuid = workflow['submission_uuid']

        staff_assessment = None
        self_assessment = None
        feedback = None
        peer_assessments = []
        has_submitted_feedback = False

        if "peer-assessment" in assessment_steps:
            peer_api.get_score(submission_uuid, self.workflow_requirements()["peer"])
            feedback = peer_api.get_assessment_feedback(submission_uuid)
            peer_assessments = [
                self._assessment_grade_context(peer_assessment)
                for peer_assessment in peer_api.get_assessments(submission_uuid)
            ]
            has_submitted_feedback = feedback is not None

        if "self-assessment" in assessment_steps:
            self_assessment = self._assessment_grade_context(
                self_api.get_assessment(submission_uuid)
            )

        raw_staff_assessment = staff_api.get_latest_staff_assessment(submission_uuid)
        if raw_staff_assessment:
            staff_assessment = self._assessment_grade_context(raw_staff_assessment)

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
            'score_explanation': self._get_score_explanation(workflow),
            'feedback_text': feedback_text,
            'has_submitted_feedback': has_submitted_feedback,
            'student_submission': create_submission_dict(student_submission, self.prompts),
            'peer_assessments': peer_assessments,
            'grade_details': self.grade_details(
                submission_uuid,
                peer_assessments=peer_assessments,
                self_assessment=self_assessment,
                staff_assessment=staff_assessment,
            ),
            'file_upload_type': self.file_upload_type,
            'allow_multiple_files': self.allow_multiple_files,
            'allow_latex': self.allow_latex,
            'prompts_type': self.prompts_type,
            'file_urls': self.get_download_urls_from_submission(student_submission),
            'xblock_id': self.get_xblock_id()
        }

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
            return step in workflow["status_details"] and not workflow["status_details"][step]["complete"]

        incomplete_steps = []
        if _is_incomplete("peer"):
            incomplete_steps.append(self._("Peer Assessment"))
        if _is_incomplete("self"):
            incomplete_steps.append(self._("Self Assessment"))

        return (
            'openassessmentblock/grade/oa_grade_incomplete.html',
            {
                'incomplete_steps': incomplete_steps,
                'xblock_id': self.get_xblock_id(),
                'score_explanation': self._get_score_explanation(workflow)
            }
        )

    @XBlock.json_handler
    def submit_feedback(self, data, suffix=''):  # pylint: disable=unused-argument
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
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api

        feedback_text = data.get('feedback_text', '')
        feedback_options = data.get('feedback_options', [])

        try:
            peer_api.set_assessment_feedback({
                'submission_uuid': self.submission_uuid,
                'feedback_text': feedback_text,
                'options': feedback_options,
            })
        except (peer_api.PeerAssessmentInternalError, peer_api.PeerAssessmentRequestError):
            return {'success': False, 'msg': self._("Assessment feedback could not be saved.")}
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
            return {'success': True, 'msg': self._("Feedback saved.")}

    def grade_details(
            self, submission_uuid, peer_assessments, self_assessment, staff_assessment,
            is_staff=False
    ):
        # pylint: disable=unicode-format-string
        """
        Returns details about the grade assigned to the submission.

        Args:
            submission_uuid (str): The id of the submission being graded.
            peer_assessments (list of dict): Serialized assessment models from the peer API.
            self_assessment (dict): Serialized assessment model from the self API
            staff_assessment (dict): Serialized assessment model from the staff API
            is_staff (bool): True if the grade details are being displayed to staff, else False.
                Default value is False (meaning grade details are being shown to the learner).

        Returns:
            A dictionary with full details about the submission's grade.

        Example:
            {
                criteria: [{
                    'label': 'Test name',
                    'name': 'f78ac7d4ca1e4134b0ba4b40ca212e72',
                    'prompt': 'Test prompt',
                    'order_num': 2,
                    'options': [...]
                    'feedback': [
                        'Good job!',
                        'Excellent work!',
                    ]
                }],
                additional_feedback: [{
                }]
                ...
            }

        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api
        from openassessment.assessment.api import self as self_api
        from openassessment.assessment.api import staff as staff_api

        criteria = copy.deepcopy(self.rubric_criteria_with_labels)

        def has_feedback(assessments):
            """
            Returns True if at least one assessment has feedback.

            Args:
                assessments: A list of assessments

            Returns:
                Returns True if at least one assessment has feedback.
            """
            return any(
                (
                    assessment and (
                        assessment.get('feedback', None) or has_feedback(assessment.get('individual_assessments', []))
                    )
                )
                for assessment in assessments
            )

        max_scores = peer_api.get_rubric_max_scores(submission_uuid)
        median_scores = None
        assessment_steps = self.assessment_steps
        if staff_assessment:
            median_scores = staff_api.get_assessment_scores_by_criteria(submission_uuid)
        elif "peer-assessment" in assessment_steps:
            median_scores = peer_api.get_assessment_median_scores(submission_uuid)
        elif "self-assessment" in assessment_steps:
            median_scores = self_api.get_assessment_scores_by_criteria(submission_uuid)

        for criterion in criteria:
            criterion_name = criterion['name']

            # Record assessment info for the current criterion
            criterion['assessments'] = self._graded_assessments(
                submission_uuid, criterion,
                assessment_steps,
                staff_assessment,
                peer_assessments,
                self_assessment,
                is_staff=is_staff,
            )

            # Record whether there is any feedback provided in the assessments
            criterion['has_feedback'] = has_feedback(criterion['assessments'])

            # Although we prevent course authors from modifying criteria post-release,
            # it's still possible for assessments created by course staff to
            # have criteria that differ from the current problem definition.
            # It's also possible to circumvent the post-release restriction
            # if course authors directly import a course into Studio.
            # If this happens, we simply leave the score blank so that the grade
            # section can render without error.
            criterion['median_score'] = median_scores.get(criterion_name, '')
            criterion['total_value'] = max_scores.get(criterion_name, '')

        return {
            'criteria': criteria,
            'additional_feedback': self._additional_feedback(
                staff_assessment=staff_assessment,
                peer_assessments=peer_assessments,
                self_assessment=self_assessment,
            ),
        }

    def _graded_assessments(
            self, submission_uuid, criterion, assessment_steps, staff_assessment, peer_assessments,
            self_assessment, is_staff=False
    ):
        """
        Returns an array of assessments with their associated grades.
        """
        def _get_assessment_part(title, feedback_title, part_criterion_name, assessment):
            """
            Returns the assessment part for the given criterion name.
            """
            if assessment:
                for part in assessment['parts']:
                    if part['criterion']['name'] == part_criterion_name:
                        part['title'] = title
                        part['feedback_title'] = feedback_title
                        return part
            return None

        # Fetch all the unique assessment parts
        criterion_name = criterion['name']
        staff_assessment_part = _get_assessment_part(
            _('Staff Grade'),
            _('Staff Comments'),
            criterion_name,
            staff_assessment
        )
        if "peer-assessment" in assessment_steps:
            peer_assessment_part = {
                'title': _('Peer Median Grade'),
                'criterion': criterion,
                'option': self._peer_median_option(submission_uuid, criterion),
                'individual_assessments': [
                    _get_assessment_part(
                        _('Peer {peer_index}').format(peer_index=index + 1),
                        _('Peer Comments'),
                        criterion_name,
                        peer_assessment
                    )
                    for index, peer_assessment in enumerate(peer_assessments)
                ],
            }
        else:
            peer_assessment_part = None
        self_assessment_part = _get_assessment_part(
            _('Self Assessment Grade') if is_staff else _('Your Self Assessment'),
            _('Your Comments'),  # This is only used in the LMS student-facing view
            criterion_name,
            self_assessment
        )

        # Now collect together all the assessments
        assessments = []
        if staff_assessment_part:
            assessments.append(staff_assessment_part)
        if peer_assessment_part:
            assessments.append(peer_assessment_part)
        if self_assessment_part:
            assessments.append(self_assessment_part)

        # Include points only for the first assessment
        if assessments:
            first_assessment = assessments[0]
            option = first_assessment['option']
            if option and option.get('points', None) is not None:
                first_assessment['points'] = option['points']

        return assessments

    def _peer_median_option(self, submission_uuid, criterion):
        """
        Returns the option for the median peer grade.

        Args:
            submission_uuid (str): The id for the submission.
            criterion (dict): The criterion in question.

        Returns:
            The option for the median peer grade.

        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.assessment.api import peer as peer_api

        median_scores = peer_api.get_assessment_median_scores(submission_uuid)
        median_score = median_scores.get(criterion['name'], None)
        median_score = -1 if median_score is None else median_score

        def median_options():
            """
            Returns a list of options that should be shown to represent the median.

            Some examples:
              1. Options A=1, B=3, and C=5, a median score of 3 returns [B].
              2. Options A=1, B=3, and C=5, a median score of 4 returns [B, C].
              3. Options A=1, B=1, and C=3, a median score of 1 returns [A, B]
              4. Options A=1, B=1, C=3, and D=3, a median score of 2 return [A, B, C, D]
              5. Options A=1, B=3 and C=5, a median score of 6 returns [C]
                 Note: 5 should not happen as a median should never be out of range.
            """
            last_score = -1
            median_options = []

            # Sort the options first by name and then by points, so that if there
            # are options with identical points they will sort alphabetically rather
            # than randomly. Note that this depends upon sorted being a stable sort.
            alphabetical_options = sorted(criterion['options'], key=lambda option: option['label'])
            ordered_options = sorted(alphabetical_options, key=lambda option: option['points'])

            for option in ordered_options:
                current_score = option['points']

                # If we have reached a new score, then decide what to do next
                if current_score != last_score:

                    # If the last score we saw was already larger than the median
                    # score, then we must have collected enough so return all
                    # the median options.
                    if last_score >= median_score:
                        return median_options

                    # If the current score is exactly the median or is less,
                    # then we don't need any previously collected scores.
                    if current_score <= median_score:
                        median_options = []

                    # Update the last score to be the current one
                    last_score = current_score

                # Collect the current option in case it is applicable
                median_options.append(option)
            return median_options

        # Calculate the full list of matching options for the median, and then:
        #  - If zero or one matches are found, then just return None or the single item.
        #  - If more than one match is found, return a dict with an aggregate label,
        #  - the median score, and no explanation (it is too verbose to show an aggregate).
        options = median_options()
        if not options:
            # If we weren't able to get a median option when there should be one, show the following message
            # This happens when there are less than must_be_graded_by assessments made for the user
            if criterion['options']:
                return {'label': _('Waiting for peer reviews')}
            return None
        if len(options) == 1:
            return options[0]
        return {
            'label': ' / '.join([option['label'] for option in options]),
            'points': median_score if median_score != -1 else None,
            'explanation': None,
        }

    def _additional_feedback(self, staff_assessment, peer_assessments, self_assessment):
        """
        Returns an array of additional feedback for the specified assessments.

        Args:
            staff_assessment: The staff assessment
            peer_assessments: An array of peer assessments
            self_assessment: The self assessment

        Returns:
            Returns an array of additional feedback per assessment.
        """
        additional_feedback = []
        if staff_assessment:
            feedback = staff_assessment.get('feedback')
            if feedback:
                additional_feedback.append({
                    'title': _('Staff Comments'),
                    'feedback': feedback
                })
        if peer_assessments and len(peer_assessments) >= self.workflow_requirements()['peer']['must_be_graded_by']:
            individual_feedback = []
            for peer_index, peer_assessment in enumerate(peer_assessments):
                individual_feedback.append({
                    'title': _('Peer {peer_index}').format(peer_index=peer_index + 1),
                    'feedback': peer_assessment.get('feedback')
                })
            if any(assessment_feedback['feedback'] for assessment_feedback in individual_feedback):
                additional_feedback.append({
                    'title': _('Peer'),
                    'individual_assessments': individual_feedback
                })
        if self_assessment:
            feedback = self_assessment.get('feedback')
            if feedback:
                additional_feedback.append({
                    'title': _('Your Comments'),
                    'feedback': feedback
                })

        return additional_feedback if additional_feedback else None

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
        if assessment is not None:
            for part in assessment['parts']:
                criterion_label_key = part['criterion']['name']
                part['criterion']['label'] = criterion_labels.get(criterion_label_key, part['criterion']['name'])

                # We need to be a little bit careful here: some assessment parts
                # have only written feedback, so they're not associated with any options.
                # If that's the case, we don't need to add the label field.
                if part.get('option') is not None:
                    option_label_key = (part['criterion']['name'], part['option']['name'])
                    part['option']['label'] = option_labels.get(option_label_key, part['option']['name'])

        return assessment

    def _get_assessment_type(self, workflow):
        """
        Determine which assessment is decisive in determining the grade.
        Args:
            workflow (dict): The serialized Workflow model.
        Returns:
            str: Type of decisive assessment. Possible values are self, staff, peer.
        """
        score = workflow['score']
        complete = score is not None

        if "staff-assessment" in self.assessment_steps:
            return "staff"

        # Edge case: staff overrides the grade.
        # If a score is overriden by staff, it'll always have an
        # attached annotation type with the `staff_defined` value,
        # so we look for that in this problem's annotation and
        # return staff if it's found.
        grade_annotation_types = [annotation['annotation_type'] for annotation in (score or {}).get("annotations", [])]
        if complete and "staff_defined" in grade_annotation_types:
            return "staff"

        # For other cases, we just need to figure out the
        # priority of each (either peer or self).
        # Just loop over the values and return the first one
        # after staff.
        for _assessment_type in workflow["assessment_score_priority"]:
            # assessment_step would always have staff in it, so skip it
            # while checking the priority here.
            if _assessment_type == "staff":
                continue

            if f"{_assessment_type}-assessment" in self.assessment_steps:
                return _assessment_type

        return None  # Just to make pylint happy

    def _get_score_explanation(self, workflow):
        """
        Return a string which explains how grade is calculated for an ORA assessment
        (which is complete i.e all assessments have been done) based on assessment_steps.
        Args:
            workflow (dict): The serialized Workflow model.
        Returns:
            str: Message explainaing how grade is determined.
        """
        score = workflow['score']
        complete = score is not None

        assessment_type = self._get_assessment_type(workflow)

        sentences = {
            "staff": _("The grade for this problem is determined by your Staff Grade."),
            "peer": _(
                "The grade for this problem is determined by the median score of "
                "your Peer Assessments."
            ),
            "self": _("The grade for this problem is determined by your Self Assessment.")
        }
        second_sentence = sentences.get(assessment_type, "")

        if complete:
            first_sentence = _(
                "You have successfully completed this problem and received a {earned_points}/{total_points}."
            ).format(earned_points=score["points_earned"], total_points=score["points_possible"])
        else:
            first_sentence = ""
            # Special Case i.e If the submission only have peer assessment
            if "peer-assessment" in self.assessment_steps and "self-assessment" not in self.assessment_steps and \
               "staff-assessment" not in self.assessment_steps:
                first_sentence = _(
                    "You have not yet received all necessary peer reviews to determine your final grade."
                )

        return f"{first_sentence} {second_sentence}".strip()

    def generate_report_data(self, user_state_iterator, limit_responses=None):
        """
        Return a list of student responses and assessments for this block in a readable way.

        Arguments:
            user_state_iterator: iterator over UserStateClient objects.
                E.g. the result of user_state_client.iter_all_for_block(block_key)
            limit_responses (int|None): maximum number of responses to include.
                Set to None (default) to include all.
        Returns:
            each call yields a tuple like:
                ("my_username", {
                    'Submission ID': 'c6551...',
                    'Item ID': 5,
                    'Anonymized Student ID': 'c801..',
                    'Assessment ID': 4,
                    'Assessment Scored Date': '2020-02-01',
                    'Assessment Scored Time': '10:03:07.218280+00:00',
                    'Assessment Type': 'PE',
                    'Anonymous Scorer Id': '6e9a...',
                    'Criterion 1: Ideas": 'Poor',
                    'Points 1': 0,
                    'Median Score 1': 0,
                    'Feedback 1': 'Does not answer the question.',
                    'Criterion 2: Content": 'Excellent',
                    'Points 2': 3,
                    'Median Score 2': 3.0,
                    'Feedback 2': 'Well described.',
                    'Criteria Count': 'Well described.',
                    'Overall Feedback': 'try again',
                    'Date/Time Final Score Given': 2020-02-01 10:03:07.218280+00:00',,
                    'Final Score Points Earned': 1,
                    'Final Score Points Possible': 5,
                    'Feedback Statements Selected': "",
                    'Feedback on Assessment': "",
                    'Response files': 'http://lms.url/...',
                    'Response': '{"file_descriptions"...}',
                    'Assessment scored At': 2020-02-01 10:03:07.218280+00:00',,
                })
        """
        from openassessment.data import OraAggregateData

        xblock_id = self.get_xblock_id()
        num_rows = 0
        for user_state in user_state_iterator:
            submission_uuid = user_state.state.get('submission_uuid')
            for row in OraAggregateData.generate_assessment_data(xblock_id, submission_uuid):
                num_rows += 1
                yield (user_state.username, row)

            if limit_responses is not None and num_rows >= limit_responses:
                # End the iterator here
                break
