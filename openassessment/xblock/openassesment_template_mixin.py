"""
Mixin to cover various template and UI related utilities
"""

from django.utils.translation import gettext as _
from web_fragments.fragment import Fragment

from openassessment.xblock.utils.defaults import (
    PEER_ASSESSMENT_MODULES,
    SELF_ASSESSMENT_MODULES,
    SELF_TO_PEER_ASSESSMENT_MODULES,
    SELF_TO_STAFF_ASSESSMENT_MODULES,
    STAFF_ASSESSMENT_MODULES,
)
from openassessment.xblock.utils.editor_config import AVAILABLE_EDITORS
from openassessment.xblock.apis.assessments.staff_assessment_api import StaffAssessmentAPI
from openassessment.xblock.load_static import LoadStatic


UI_MODELS = {
    "submission": {
        "name": "submission",
        "class_id": "step--response",
        "title": "Your Response"
    },
    "student-training": {
        "name": "student-training",
        "class_id": "step--student-training",
        "title": "Learn to Assess Responses"
    },
    "peer-assessment": {
        "name": "peer-assessment",
        "class_id": "step--peer-assessment",
        "title": "Assess Peers"
    },
    "self-assessment": {
        "name": "self-assessment",
        "class_id": "step--self-assessment",
        "title": "Assess Your Response"
    },
    "staff-assessment": {
        "name": "staff-assessment",
        "class_id": "step--staff-assessment",
        "title": "Staff Grade"
    },
    "grade": {
        "name": "grade",
        "class_id": "step--grade",
        "title": "Your Grade:"
    },
    "leaderboard": {
        "name": "leaderboard",
        "class_id": "step--leaderboard",
        "title": "Top Responses"
    }
}


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
    }

    @classmethod
    def templates(cls):
        """
        Returns a list of dictionary field: value objects that describe possible templates.
        """
        templates = []
        for assessment_type, display_name in cls.VALID_ASSESSMENT_TYPES_DISPLAY_NAMES.items():
            template_id = assessment_type
            template = cls._create_template_dict(template_id, display_name)
            templates.append(template)
        return templates

    @classmethod
    def filter_templates(cls, template, _):
        """
        Filters the list of templates for the template view. Filter out only peer-assessment, because peer-assessment
        is the "default" template we use for ORA. Without this, it would display twice.
        See get_component_templates in studio.
        """
        return template['template_id'] != 'peer-assessment'

    @classmethod
    def _create_template_dict(cls, template_id, display_name):
        """
        Creates a dictionary for serving various metadata for the template.

        Args:
            template_id(str): template id of what assessment template needs to be served.
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
            template_id(str): template id of what assessment template needs to be served.

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
            template_id(str): template id of what assessment template needs to be served.

        Returns:
            A dictionary of payload to be consumed by Studio.
        """
        assessment_module = cls.VALID_ASSESSMENT_TYPES_ASSESSMENT_MODULE \
            .get(template_id)
        return {
            "rubric_assessments": assessment_module
        }

    def _create_ui_models(self):
        """Combine UI attributes and XBlock configuration into a UI model.

        This method takes all configuration for this XBlock instance and appends
        UI attributes to create a UI Model for rendering all assessment modules.
        This allows a clean separation of static UI attributes from persistent
        XBlock configuration.

        """
        ui_models = [UI_MODELS["submission"]]
        staff_assessment_required = False
        for assessment in self.valid_assessments:
            if assessment["name"] == "staff-assessment":
                if not assessment["required"]:
                    continue
                staff_assessment_required = True
            ui_model = UI_MODELS.get(assessment["name"])
            if ui_model:
                ui_models.append(dict(assessment, **ui_model))

        if not staff_assessment_required and StaffAssessmentAPI.staff_assessment_exists(self.submission_uuid):
            ui_models.append(UI_MODELS["staff-assessment"])

        ui_models.append(UI_MODELS["grade"])

        if self.leaderboard_show > 0 and not self.teams_enabled:
            ui_models.append(UI_MODELS["leaderboard"])

        return ui_models

    def _create_fragment(
        self,
        template,
        context_dict,
        initialize_js_func,
        additional_css=None,
        additional_js=None,
        additional_js_context=None
    ):
        """
        Creates a fragment for display.

        """
        fragment = Fragment(template.render(context_dict))

        if additional_css is None:
            additional_css = []
        if additional_js is None:
            additional_js = []

        i18n_service = self.runtime.service(self, 'i18n')
        if hasattr(i18n_service, 'get_language_bidi') and i18n_service.get_language_bidi():
            css_url = LoadStatic.get_url("openassessment-rtl.css")
        else:
            css_url = LoadStatic.get_url("openassessment-ltr.css")

        # TODO: load CSS and JavaScript as URLs once they can be served by the CDN
        for css in additional_css:
            fragment.add_css_url(css)
        fragment.add_css_url(css_url)

        # minified additional_js should be already included in 'make javascript'
        fragment.add_javascript_url(LoadStatic.get_url("openassessment-lms.js"))

        js_context_dict = {
            "ALLOWED_IMAGE_MIME_TYPES": self.ALLOWED_IMAGE_MIME_TYPES,
            "ALLOWED_FILE_MIME_TYPES": self.ALLOWED_FILE_MIME_TYPES,
            "FILE_EXT_BLACK_LIST": self.FILE_EXT_BLACK_LIST,
            "FILE_TYPE_WHITE_LIST": self.white_listed_file_types,
            "MAXIMUM_FILE_UPLOAD_COUNT": self.MAX_FILES_COUNT,
            "TEAM_ASSIGNMENT": self.is_team_assignment(),
            "AVAILABLE_EDITORS": AVAILABLE_EDITORS,
            "TEXT_RESPONSE_EDITOR": self.text_response_editor,
        }
        # If there's any additional data to be passed down to JS
        # include it in the context dict
        if additional_js_context:
            js_context_dict.update({"CONTEXT": additional_js_context})

        fragment.initialize_js(initialize_js_func, js_context_dict)
        return fragment
