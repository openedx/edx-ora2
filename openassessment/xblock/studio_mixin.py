"""
Studio editing view for OpenAssessment XBlock.
"""
from django.template import Context
import pkg_resources
import copy
import logging
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from voluptuous import MultipleInvalid
from xblock.core import XBlock
from xblock.fragment import Fragment
from openassessment.xblock import xml
from openassessment.xblock.validation import validator
from openassessment.xblock.data_conversion import create_rubric_dict
from openassessment.xblock.schema import EDITOR_UPDATE_SCHEMA


logger = logging.getLogger(__name__)


class StudioMixin(object):
    """
    Studio editing view for OpenAssessment XBlock.
    """

    DEFAULT_CRITERIA = [
        {
            'options': [
                {
                },
            ]
        }
    ]

    def studio_view(self, context=None):
        """
        Render the OpenAssessment XBlock for editing in Studio.

        Args:
            context: Not actively used for this view.

        Returns:
            (Fragment): An HTML fragment for editing the configuration of this XBlock.
        """
        rendered_template = get_template(
            'openassessmentblock/edit/oa_edit.html'
        ).render(Context(self.editor_context()))
        frag = Fragment(rendered_template)
        frag.add_javascript(pkg_resources.resource_string(__name__, "static/js/openassessment-studio.min.js"))
        frag.initialize_js('OpenAssessmentEditor')
        return frag

    def editor_context(self):
        """
        Retrieve the XBlock's content definition.

        Returns:
            dict with keys
                'rubric' (unicode), 'prompt' (unicode), 'title' (unicode),
                'submission_start' (unicode),  'submission_due' (unicode),
                'assessments (dict)

        """
        # Copies the rubric assessments so that we can change student
        # training examples from dict -> str without negatively modifying
        # the openassessmentblock definition.
        # Django Templates cannot handle dict keys with dashes, so we'll convert
        # the dashes to underscores.
        assessments = {}
        for assessment in self.rubric_assessments:
            name = assessment['name']
            assessments[name.replace('-', '_')] = copy.deepcopy(
                assessment
            )

        student_training_module = self.get_assessment_module(
            'student-training'
        )
        if student_training_module:
            student_training_module = copy.deepcopy(student_training_module)
            try:
                examples = xml.serialize_examples_to_xml_str(
                    student_training_module
                )
                student_training_module["examples"] = examples
                assessments['training'] = student_training_module
            # We do not expect serialization to raise an exception, but if it does,
            # handle it gracefully.
            except:
                logger.exception("An error occurred while serializing the XBlock")

        submission_due = self.submission_due if self.submission_due else ''
        submission_start = self.submission_start if self.submission_start else ''

        # Every rubric requires one criterion. If there is no criteria
        # configured for the XBlock, return one empty default criterion, with
        # an empty default option.
        criteria = copy.deepcopy(self.rubric_criteria)
        if not criteria:
            criteria = self.DEFAULT_CRITERIA

        return {
            'prompt': self.prompt,
            'title': self.title,
            'submission_due': submission_due,
            'submission_start': submission_start,
            'assessments': assessments,
            'criteria': criteria,
            'feedbackprompt': unicode(self.rubric_feedback_prompt),
        }

    @XBlock.json_handler
    def update_editor_context(self, data, suffix=''):
        """
        Update the XBlock's configuration.

        Args:
            data (dict): Data from the request; should have a value for the keys: 'rubric', 'prompt',
            'title', 'submission_start', 'submission_due', and 'assessments'.
                -- The 'rubric' should be an XML representation of the new rubric.
                -- The 'prompt' and 'title' should be plain text.
                -- The dates 'submission_start' and 'submission_due' are both ISO strings
                -- The 'assessments' is a list of assessment dictionaries (much like self.rubric_assessments)
                   with the notable exception that all examples (for Student Training and eventually AI)
                   are in XML string format and need to be parsed into dictionaries.

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool) and 'msg' (str)
        """

        # Validate and sanitize the data using a schema
        # If the data is invalid, this means something is wrong with
        # our JavaScript, so we log an exception.
        try:
            data = EDITOR_UPDATE_SCHEMA(data)
        except MultipleInvalid:
            logger.exception('Editor context is invalid')
            return {'success': False, 'msg': _('Error updating XBlock configuration')}

        xblock_validator = validator(self)
        success, msg = xblock_validator(
            create_rubric_dict(data['prompt'], data['criteria']),
            data['assessments'],
            submission_start=data['submission_start'],
            submission_due=data['submission_due'],
        )
        if not success:
            return {'success': False, 'msg': _('Validation error: {error}').format(error=msg)}

        # At this point, all the input data has been validated,
        # so we can safely modify the XBlock fields.
        self.title = data['title']
        self.prompt = data['prompt']
        self.rubric_criteria = data['criteria']
        self.rubric_assessments = data['assessments']
        self.rubric_feedback_prompt = data['feedback_prompt']
        self.submission_start = data['submission_start']
        self.submission_due = data['submission_due']

        return {'success': True, 'msg': _(u'Successfully updated OpenAssessment XBlock')}

    @XBlock.json_handler
    def check_released(self, data, suffix=''):
        """
        Check whether the problem has been released.

        Args:
            data (dict): Not used

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool), 'message' (unicode), and 'is_released' (bool)
        """
        # There aren't currently any server-side error conditions we report to the client,
        # but we send success/msg values anyway for consistency with other handlers.
        return {
            'success': True, 'msg': u'',
            'is_released': self.is_released()
        }
