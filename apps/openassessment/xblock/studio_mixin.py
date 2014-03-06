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
from openassessment.xblock.xml import (
    serialize_content, update_from_xml_str,
    UpdateFromXmlError, InvalidRubricError,
    InvalidAssessmentsError, InvalidDatesError
)

from openassessment.peer.serializers import (
    validate_assessments, validate_rubric, validate_dates
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
                # Temporary: enforce the requirement that there must be exactly
                # two assessments: peer followed by self.
                assessments_validator = \
                    lambda arg: validate_assessments(arg, enforce_peer_then_self=True)

                update_from_xml_str(
                    self, data['xml'],
                    rubric_validator=validate_rubric,
                    assessments_validator=assessments_validator,
                    dates_validator=validate_dates
                )

            except InvalidRubricError:
                return {'success': False, 'msg': _('Rubric definition was not valid.')}

            except InvalidAssessmentsError as ex:
                return {'success': False,
                        'msg': _('Assessment definitions were not valid: {error}').format(error=ex.message)}

            except InvalidDatesError as ex:
                return {'success': False, 'msg': _('Dates were not valid: {error}').format(error=ex.message)}

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
