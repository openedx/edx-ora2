"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import logging
from django.template.context import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from xblock.core import XBlock
from xblock.fragment import Fragment
from openassessment.xblock.xml import(
    serialize_content, parse_rubric_xml, parse_assessments_xml, UpdateFromXmlError, serialize_rubric_to_xml_str,
    serialize_assessments_to_xml_str
)

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
    def update_xml(self, data, suffix=''):
        """
        Update the XBlock's XML.

        Args:
            data (dict): Data from the request; should have a value for the key 'xml'
                containing the XML for this XBlock.

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool) and 'msg' (str)
        """
        if 'rubric' not in data:
            return {'success': False, 'msg': _('Must specify "rubric" in request JSON dict.')}

        if 'settings' not in data:
            return {'success': False, 'msg': _('Must specify "settings" in request JSON dict.')}

        if 'prompt' not in data:
            return {'success': False, 'msg': _('Must specify "prompt" in request JSON dict.')}

        settings = data['settings']
        try:
            rubric = parse_rubric_xml(data['rubric'])
            assessments = parse_assessments_xml(settings['assessments'])
            submission_due = settings["submission_due"]
        except UpdateFromXmlError as ex:
            return {'success': False, 'msg': _('An error occurred while saving: {error}').format(error=ex)}

        xblock_validator = validator(self)
        success, msg = xblock_validator(rubric, {'due': submission_due}, assessments)
        if not success:
            return {'success': False, 'msg': _('Validation error: {error}').format(error=msg)}

        self.update(
            rubric,
            assessments,
            settings["submission_due"],
            settings["submission_start"],
            settings["title"],
            data['prompt']
        )
        return {'success': True, 'msg': _('Successfully updated OpenAssessment XBlock')}

    def update(self, rubric, assessments, submission_due, submission_start, title, prompt):
        """
        Given a dictionary of properties, update the XBlock

        """
        # If we've gotten this far, then we've successfully parsed the XML
        # and validated the contents.  At long last, we can safely update the XBlock.
        self.title = title
        self.prompt = prompt
        self.rubric_criteria = rubric['criteria']
        self.rubric_assessments = assessments
        self.rubric_feedback_prompt = rubric['feedback_prompt']
        self.submission_start = submission_start
        self.submission_due = submission_due

    @XBlock.json_handler
    def xml(self, data, suffix=''):
        """
        Retrieve the XBlock's content definition, serialized as XML.

        Args:
            data (dict): Not used

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool), 'message' (unicode), and 'xml' (unicode)
        """
        try:
            rubric = serialize_rubric_to_xml_str(self)
            prompt = self.prompt
            settings = {
                'title': self.title,
                'submission_start': self.submission_start,
                'submission_due': self.submission_due,
                'assessments': serialize_assessments_to_xml_str(self)
            }
        # We do not expect `serialize_content` to raise an exception,
        # but if it does, handle it gracefully.
        except Exception as ex:
            msg = _('An unexpected error occurred while loading the problem: {error}').format(error=ex)
            logger.error(msg)
            return {'success': False, 'msg': msg, 'xml': u''}
        else:
            return {'success': True, 'msg': '', 'prompt': prompt, 'rubric': rubric, 'settings': settings}

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