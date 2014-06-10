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
            data (dict): Data from the request; should have a value for the keys
                'rubric', 'settings' and 'prompt'. The 'rubric' should be an XML
                representation of the new rubric. The 'prompt' should be a plain
                text prompt. The 'settings' should be a dict of 'title',
                'submission_due', 'submission_start' and the XML configuration for
                all 'assessments'.

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool) and 'msg' (str)
        """
        missing_keys = list({'rubric', 'settings', 'prompt'} - set(data.keys()))
        if missing_keys:
            logger.warn(
                'Must specify the following keys in request JSON dict: {}'.format(missing_keys)
            )
            return {'success': False, 'msg': _('Error updating XBlock configuration')}
        settings = data['settings']
        try:

            rubric = xml.parse_rubric_xml_str(data['rubric'])
            assessments = xml.parse_assessments_xml_str(settings['assessments'])
            submission_due = settings["submission_due"]
        except xml.UpdateFromXmlError as ex:
            return {'success': False, 'msg': _('An error occurred while saving: {error}').format(error=ex)}

        xblock_validator = validator(self)
        success, msg = xblock_validator(rubric, {'due': submission_due}, assessments)
        if not success:
            return {'success': False, 'msg': _('Validation error: {error}').format(error=msg)}

        self.update(
            rubric['criteria'],
            rubric['feedbackprompt'],
            assessments,
            settings["submission_due"],
            settings["submission_start"],
            settings["title"],
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
            dict with keys 'success' (bool), 'message' (unicode),
                'rubric' (unicode), 'prompt' (unicode), and 'settings' (dict)

        """
        try:
            assessments = xml.serialize_assessments_to_xml_str(self)
            rubric = xml.serialize_rubric_to_xml_str(self)
        # We do not expect serialization to raise an exception,
        # but if it does, handle it gracefully.
        except Exception as ex:
            msg = _('An unexpected error occurred while loading the problem: {error}').format(error=ex)
            logger.error(msg)
            return {'success': False, 'msg': msg, 'xml': u''}

        # Populates the context for the assessments section of the editing
        # panel. This will adjust according to the fields laid out in this
        # section.
        settings = {
            'submission_due': self.submission_due,
            'submission_start': self.submission_start,
            'title': self.title,
            'assessments': assessments
        }

        return {
            'success': True,
            'msg': '',
            'rubric': rubric,
            'prompt': self.prompt,
            'settings': settings
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
