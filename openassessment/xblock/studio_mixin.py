"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import copy
import logging
from django.template.context import Context
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

    def studio_view(self, context=None):
        """
        Render the OpenAssessment XBlock for editing in Studio.

        Args:
            context: Not actively used for this view.

        Returns:
            (Fragment): An HTML fragment for editing the configuration of this XBlock.
        """
        rendered_template = get_template('openassessmentblock/oa_edit.html').render(Context({}))
        frag = Fragment(rendered_template)
        frag.add_javascript(pkg_resources.resource_string(__name__, "static/js/openassessment.min.js"))
        frag.initialize_js('OpenAssessmentEditor')
        return frag

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
    def editor_context(self, data, suffix=''):
        """
        Retrieve the XBlock's content definition, serialized as a JSON object
        containing all the configuration as it will be displayed for studio
        editing.

        Args:
            data (dict): Not used

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys
                'success' (bool),  'message' (unicode),  'rubric' (unicode),  'prompt' (unicode),
                'title' (unicode),  'submission_start' (unicode),  'submission_due' (unicode),  'assessments (dict)

        """
        try:
            # Copies the rubric assessments so that we can change student training examples from dict -> str without
            # negatively modifying the openassessmentblock definition.
            assessment_list = copy.deepcopy(self.rubric_assessments)
            # Finds the student training dictionary, if it exists, and replaces the examples with their XML definition
            student_training_dictionary = [d for d in assessment_list if d["name"] == "student-training"]
            if student_training_dictionary:
                # Our for loop will return a list.  Select the first element of that list if it exists.
                student_training_dictionary = student_training_dictionary[0]
                examples = xml.serialize_examples_to_xml_str(student_training_dictionary)
                student_training_dictionary["examples"] = examples

        # We do not expect serialization to raise an exception, but if it does, handle it gracefully.
        except:
            logger.exception("An error occurred while serializing the XBlock")
            msg = _('An unexpected error occurred while loading the problem')
            return {'success': False, 'msg': msg, 'xml': u''}

        # Populates the context for the assessments section of the editing
        # panel. This will adjust according to the fields laid out in this
        # section.

        submission_due = self.submission_due if self.submission_due else ''
        submission_start = self.submission_start if self.submission_start else ''

        rubric_dict = {
            'criteria' : self.rubric_criteria,
            'feedbackprompt': unicode(self.rubric_feedback_prompt)
        }

        return {
            'success': True,
            'msg': '',
            'rubric': rubric_dict,
            'prompt': self.prompt,
            'submission_due': submission_due,
            'submission_start': submission_start,
            'title': self.title,
            'assessments': assessment_list
        }

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
