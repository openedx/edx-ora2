"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import logging
import dateutil.parser
from django.template.context import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from xblock.core import XBlock
from xblock.fragment import Fragment
from openassessment.xblock.xml import (
    serialize_content, update_from_xml,
    UpdateFromXmlError, InvalidRubricError
)
from openassessment.peer.serializers import (
    rubric_from_dict, AssessmentSerializer, InvalidRubric
)


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
        frag.add_javascript(pkg_resources.resource_string(__name__, "static/js/src/oa_server.js"))
        frag.add_javascript(pkg_resources.resource_string(__name__, "static/js/src/oa_edit.js"))
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
        if 'xml' in data:
            try:
                update_from_xml(
                    self, data['xml'],
                    rubric_validator=self._validate_rubric,
                    assessment_validator=self._validate_assessment
                )

            except InvalidRubricError:
                return {'success': False, 'msg': _('Rubric definition was not valid.')}

            except UpdateFromXmlError as ex:
                return {'success': False, 'msg': _('An error occurred while saving: {error}').format(error=ex.message)}

            else:
                return {'success': True, 'msg': _('Successfully updated OpenAssessment XBlock')}

        else:
            return {'success': False, 'msg': _('Must specify "xml" in request JSON dict.')}

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
            xml = serialize_content(self)

        # We do not expect `serialize_content` to raise an exception,
        # but if it does, handle it gracefully.
        except Exception as ex:
            msg = _('An unexpected error occurred while loading the problem: {error}').format(error=ex.message)
            logger.error(msg)
            return {'success': False, 'msg': msg, 'xml': u''}
        else:
            return {'success': True, 'msg': '', 'xml': xml}

    def _validate_rubric(self, rubric_dict):
        """
        Check that the rubric is semantically valid.

        Args:
            rubric_dict (dict): Serialized Rubric model from the peer grading app.

        Returns:
            boolean indicating whether the rubric is semantically valid.
        """
        try:
            rubric_from_dict(rubric_dict)
        except InvalidRubric as ex:
            return (False, ex.message)
        else:
            return (True, u'')

    def _validate_assessment(self, assessment_dict):
        """
        Check that the assessment is semantically valid.

        Args:
            assessment (dict): Serialized Assessment model from the peer grading app.

        Returns:
            boolean indicating whether the assessment is semantically valid.
        """
        # Supported assessment
        if not assessment_dict.get('name') in ['peer-assessment', 'self-assessment']:
            return (False, _("Assessment type is not supported"))

        # Number you need to grade is >= the number of people that need to grade you
        if assessment_dict.get('must_grade') < assessment_dict.get('must_be_graded_by'):
            return (False, _('"must_grade" should be less than "must_be_graded_by"'))

        # Due date is after start date, if both are specified.
        start_datetime = assessment_dict.get('start_datetime')
        due_datetime = assessment_dict.get('due_datetime')

        if start_datetime is not None and due_datetime is not None:
            start = dateutil.parser.parse(assessment_dict.get('start_datetime'))
            due = dateutil.parser.parse(assessment_dict.get('due_datetime'))

            if start > due:
                return (False, _('Due date must be after start date'))

        return (True, u'')
