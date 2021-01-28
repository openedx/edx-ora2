"""
    Open Assessment Template mixin helps out in generating different presets to display in studio.
"""
from django.utils.translation import ugettext as _

from openassessment.xblock.defaults import (PEER_ASSESSMENT_MODULES, SELF_ASSESSMENT_MODULES,
                                            SELF_TO_PEER_ASSESSMENT_MODULES, SELF_TO_STAFF_ASSESSMENT_MODULES,
                                            STAFF_ASSESSMENT_MODULES, BLANK_ASSESSMENT_MODULES)


class OpenAssessmentTemplatesMixin:
    """
    This helps to get templates for different type of assessment that is
    offered.
    """

    VALID_ASSESSMENT_TYPES_DISPLAY_NAMES = {
        "peer-assessment": _("Peer Assessment Only"),
        "self-assessment": _("Self Assessment Only"),
        "staff-assessment": _("Staff Assessment Only"),
        "self-to-peer": _("Self Assessment to Peer Assessment"),
        "self-to-staff": _("Self Assessment to Staff Assessment")
    }

    VALID_ASSESSMENT_TYPES_ASSESSMENT_MODULE = {
        "self-assessment": SELF_ASSESSMENT_MODULES,
        "peer-assessment": PEER_ASSESSMENT_MODULES,
        "staff-assessment": STAFF_ASSESSMENT_MODULES,
        "self-to-peer": SELF_TO_PEER_ASSESSMENT_MODULES,
        "self-to-staff": SELF_TO_STAFF_ASSESSMENT_MODULES,
        "blank-assessment": BLANK_ASSESSMENT_MODULES
    }

    @classmethod
    def templates(cls):
        """
        Returns a list of dictionary field: value objects that describe possible templates.
        """
        templates = []
        for assesment_type, display_name in cls.VALID_ASSESSMENT_TYPES_DISPLAY_NAMES.items():
            template_id = assesment_type
            template = cls._create_template_dict(template_id, display_name)
            templates.append(template)
        return templates

    @classmethod
    def _create_template_dict(cls, template_id, display_name):
        """
        Creates a dictionary for serving various metadata for the template.

        Args:
            template_id(str): template id of what assessement template needs to be served.
            display_name(str): display name of template.

        Returns:
            A dictionary with proper keys to be consumed.
        """
        return {
            "template_id": template_id,
            "metadata": {
                "display_name": display_name,
            }
        }

    @classmethod
    def get_template(cls, template_id):
        """
        Helps to generate various option level template for ORA.

        Args:
            template_id(str): template id of what assessement template needs to be served.

        Returns:
            A dictionary of payload to be consumed by Studio.
        """
        rubric_assessments = cls._create_rubric_assessment_dict(template_id)
        return {
            "data": rubric_assessments
        }

    @classmethod
    def _create_rubric_assessment_dict(cls, template_id):
        """
        Creates a dictionary of parameters to be passed while creating ORA xblock.

        Args:
            template_id(str): template id of what assessement template needs to be served.

        Returns:
            A dictionary of payload to be consumed by Studio.
        """
        assessment_module = cls.VALID_ASSESSMENT_TYPES_ASSESSMENT_MODULE \
            .get(template_id)
        return {
            "rubric_assessments": assessment_module
        }
