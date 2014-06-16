"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import copy
import logging
from django.template.context import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from xblock.core import XBlock
from xblock.fragment import Fragment
from openassessment.xblock import xml
from openassessment.xblock.validation import validator


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
                -- The 'assessments' is a list of asessment dictionaries (much like self.rubric_assessments)
                   with the notable exception that all examples (for Student Training and eventually AI)
                   are in XML string format and need to be parsed into dictionaries.

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool) and 'msg' (str)
        """
        missing_keys = list(
            {'rubric', 'prompt', 'title', 'assessments', 'submission_start', 'submission_due'} - set(data.keys())
        )
        if missing_keys:
            logger.warn(
                'Must specify the following missing keys in request JSON dict: {}'.format(missing_keys)
            )
            return {'success': False, 'msg': _('Error updating XBlock configuration')}

        try:
            rubric = xml.parse_rubric_xml_str(data["rubric"])
            submission_due = xml.parse_date(data["submission_due"])
            submission_start = xml.parse_date(data["submission_start"])
            assessments = xml.parse_assessment_dictionaries(data["assessments"])
        except xml.UpdateFromXmlError as ex:
            return {'success': False, 'msg': _('An error occurred while saving: {error}').format(error=ex)}

        xblock_validator = validator(self)
        success, msg = xblock_validator(rubric, {'due': submission_due, 'start': submission_start}, assessments)
        if not success:
            return {'success': False, 'msg': _('Validation error: {error}').format(error=msg)}

        self.update(
            rubric['criteria'],
            rubric['feedbackprompt'],
            assessments,
            submission_due,
            submission_start,
            data["title"],
            data["prompt"]
        )
        return {'success': True, 'msg': 'Successfully updated OpenAssessment XBlock'}

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
            rubric = xml.serialize_rubric_to_xml_str(self)

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
        except Exception as ex:
            msg = _('An unexpected error occurred while loading the problem: {error}').format(error=ex)
            logger.error(msg)
            return {'success': False, 'msg': msg, 'xml': u''}

        # Populates the context for the assessments section of the editing
        # panel. This will adjust according to the fields laid out in this
        # section.

        submission_due = self.submission_due if self.submission_due else ''

        submission_start = self.submission_start if self.submission_start else ''

        return {
            'success': True,
            'msg': '',
            'rubric': rubric,
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

