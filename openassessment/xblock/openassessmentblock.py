"""An XBlock where students can read a question and compose their response"""

import copy
import datetime as dt
import json
import logging
import os
import re

import pkg_resources
import pytz

from django.conf import settings
from django.template.loader import get_template

from bleach.sanitizer import Cleaner
from lazy import lazy
from webob import Response
from xblock.core import XBlock
from xblock.exceptions import NoSuchServiceError
from xblock.fields import Boolean, Integer, List, Scope, String
from web_fragments.fragment import Fragment

from openassessment.staffgrader.staff_grader_mixin import StaffGraderMixin
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.course_items_listing_mixin import CourseItemsListingMixin
from openassessment.xblock.data_conversion import create_prompts_list, create_rubric_dict, update_assessments_format
from openassessment.xblock.defaults import *  # pylint: disable=wildcard-import, unused-wildcard-import
from openassessment.xblock.grade_mixin import GradeMixin
from openassessment.xblock.leaderboard_mixin import LeaderboardMixin
from openassessment.xblock.lms_mixin import LmsCompatibilityMixin
from openassessment.xblock.message_mixin import MessageMixin
from openassessment.xblock.mobile import togglable_mobile_support
from openassessment.xblock.peer_assessment_mixin import PeerAssessmentMixin
from openassessment.xblock.resolve_dates import (
    DateValidationError, DISTANT_FUTURE, DISTANT_PAST, parse_date_value, resolve_dates
)
from openassessment.xblock.rubric_reuse_mixin import RubricReuseMixin
from openassessment.xblock.self_assessment_mixin import SelfAssessmentMixin
from openassessment.xblock.staff_area_mixin import StaffAreaMixin
from openassessment.xblock.staff_assessment_mixin import StaffAssessmentMixin
from openassessment.xblock.student_training_mixin import StudentTrainingMixin
from openassessment.xblock.studio_mixin import StudioMixin
from openassessment.xblock.submission_mixin import SubmissionMixin
from openassessment.xblock.team_mixin import TeamMixin
from openassessment.xblock.validation import validator
from openassessment.xblock.config_mixin import ConfigMixin
from openassessment.xblock.workflow_mixin import WorkflowMixin
from openassessment.xblock.team_workflow_mixin import TeamWorkflowMixin
from openassessment.xblock.openassesment_template_mixin import OpenAssessmentTemplatesMixin
from openassessment.xblock.xml import parse_from_xml, serialize_content_to_xml
from openassessment.xblock.editor_config import AVAILABLE_EDITORS
from openassessment.xblock.load_static import LoadStatic

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


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


def load(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")


@XBlock.needs("i18n")
@XBlock.needs("user")
@XBlock.needs("user_state")
@XBlock.needs("teams")
@XBlock.needs("teams_configuration")
class OpenAssessmentBlock(MessageMixin,
                          SubmissionMixin,
                          PeerAssessmentMixin,
                          SelfAssessmentMixin,
                          StaffAssessmentMixin,
                          StudioMixin,
                          GradeMixin,
                          LeaderboardMixin,
                          StaffAreaMixin,
                          WorkflowMixin,
                          TeamWorkflowMixin,
                          StudentTrainingMixin,
                          LmsCompatibilityMixin,
                          CourseItemsListingMixin,
                          ConfigMixin,
                          TeamMixin,
                          OpenAssessmentTemplatesMixin,
                          RubricReuseMixin,
                          StaffGraderMixin,
                          XBlock):
    """Displays a prompt and provides an area where students can compose a response."""

    VALID_ASSESSMENT_TYPES = [
        "student-training",
        "peer-assessment",
        "self-assessment",
        "staff-assessment",
    ]

    VALID_ASSESSMENT_TYPES_FOR_TEAMS = [  # pylint: disable=invalid-name
        'staff-assessment',
    ]

    public_dir = 'static'

    submission_start = String(
        default=DEFAULT_START, scope=Scope.settings,
        help="ISO-8601 formatted string representing the submission start date."
    )

    submission_due = String(
        default=DEFAULT_DUE, scope=Scope.settings,
        help="ISO-8601 formatted string representing the submission due date."
    )

    text_response_raw = String(
        help="Specify whether learners must include a text based response to this problem's prompt.",
        default="required",
        scope=Scope.settings
    )

    text_response_editor = String(
        help="Select which editor learners will use to include a text based response to this problem's prompt.",
        scope=Scope.settings,
        default='text'
    )

    file_upload_response_raw = String(
        help="Specify whether learners are able to upload files as a part of their response.",
        default=None,
        scope=Scope.settings
    )

    allow_file_upload = Boolean(
        default=False,
        scope=Scope.content,
        help="Do not use. For backwards compatibility only."
    )

    file_upload_type_raw = String(
        default=None,
        scope=Scope.content,
        help="File upload to be included with submission (can be 'image', 'pdf-and-image', or 'custom')."
    )

    white_listed_file_types = List(
        default=[],
        scope=Scope.content,
        help="Custom list of file types allowed with submission."
    )

    allow_multiple_files = Boolean(
        default=True,
        scope=Scope.settings,
        help="Allow multiple files uploaded with submission (if file upload enabled)."
    )

    allow_latex = Boolean(
        default=False,
        scope=Scope.settings,
        help="Latex rendering allowed with submission."
    )

    title = String(
        default="Open Response Assessment",
        scope=Scope.content,
        help="A title to display to a student (plain text)."
    )

    leaderboard_show = Integer(
        default=0,
        scope=Scope.content,
        help="The number of leaderboard results to display (0 if none)"
    )

    prompt = String(
        default=DEFAULT_PROMPT,
        scope=Scope.content,
        help="The prompts to display to a student."
    )

    prompts_type = String(
        default='text',
        scope=Scope.content,
        help="The type of prompt. html or text"
    )

    rubric_criteria = List(
        default=DEFAULT_RUBRIC_CRITERIA,
        scope=Scope.content,
        help="The different parts of grading for students giving feedback."
    )

    rubric_feedback_prompt = String(
        default=DEFAULT_RUBRIC_FEEDBACK_PROMPT,
        scope=Scope.content,
        help="The rubric feedback prompt displayed to the student"
    )

    rubric_feedback_default_text = String(
        default=DEFAULT_RUBRIC_FEEDBACK_TEXT,
        scope=Scope.content,
        help="The default rubric feedback text displayed to the student"
    )

    rubric_assessments = List(
        default=DEFAULT_ASSESSMENT_MODULES,
        scope=Scope.content,
        help="The requested set of assessments and the order in which to apply them."
    )

    submission_uuid = String(
        default=None,
        scope=Scope.user_state,
        help="The student's submission that others will be assessing."
    )

    has_saved = Boolean(
        default=False,
        scope=Scope.user_state,
        help="Indicates whether the user has saved a response."
    )

    saved_response = String(
        default="",
        scope=Scope.user_state,
        help="Saved response submission for the current user."
    )

    saved_files_descriptions = String(
        default="",
        scope=Scope.user_state,
        help="Saved descriptions for each uploaded file."
    )

    saved_files_names = String(
        default="",
        scope=Scope.user_state,
        help="Saved original names for each uploaded file."
    )

    saved_files_sizes = String(
        default="",
        scope=Scope.user_state,
        help="Filesize of each uploaded file in bytes."
    )

    no_peers = Boolean(
        default=False,
        scope=Scope.user_state,
        help="Indicates whether or not there are peers to grade."
    )

    teams_enabled = Boolean(
        default=False,
        scope=Scope.settings,
        help="Whether team submissions are enabled for this case study.",
    )

    selected_teamset_id = String(
        default="",
        scope=Scope.settings,
        help="The id of the selected teamset.",
    )

    show_rubric_during_response = Boolean(
        default=False,
        scope=Scope.settings,
        help="Should the rubric be visible to learners in the response section?"
    )

    @property
    def course_id(self):
        return str(self.xmodule_runtime.course_id)  # pylint: disable=no-member

    @property
    def text_response(self):
        """
        Backward compatibility for existing blocks that were created without text_response
        or file_upload_response fields. These blocks will be treated as required text.
        """
        if not self.file_upload_response_raw and not self.text_response_raw:
            return 'required'
        return self.text_response_raw

    @text_response.setter
    def text_response(self, value):
        """
        Setter for text_response_raw
        """
        self.text_response_raw = value if value else None

    @property
    def file_upload_response(self):
        """
        Backward compatibility for existing block before that were created without
        'text_response' and 'file_upload_response_raw' fields.
        """
        if not self.file_upload_response_raw and (self.file_upload_type_raw is not None or self.allow_file_upload):
            return 'optional'
        return self.file_upload_response_raw

    @file_upload_response.setter
    def file_upload_response(self, value):
        """
        Setter for file_upload_response_raw
        """
        self.file_upload_response_raw = value if value else None

    @property
    def file_upload_type(self):
        """
        Backward compatibility for existing block before the change from allow_file_upload to file_upload_type_raw.

        This property will use new file_upload_type_raw field when available, otherwise will fall back to
        allow_file_upload field for old blocks.
        """
        if self.file_upload_type_raw is not None:
            return self.file_upload_type_raw
        if self.allow_file_upload:
            return 'image'
        return None

    @file_upload_type.setter
    def file_upload_type(self, value):
        """
        Setter for file_upload_type_raw
        """
        self.file_upload_type_raw = value

    @property
    def white_listed_file_types_string(self):
        """
        Join the white listed file types into comma delimited string
        """
        if self.white_listed_file_types:
            return ','.join(self.white_listed_file_types)
        return ''

    @white_listed_file_types_string.setter
    def white_listed_file_types_string(self, value):
        """
        Convert comma delimited white list string into list with some clean up
        """
        self.white_listed_file_types = [file_type.strip().strip('.').lower()
                                        for file_type in value.split(',')] if value else None

    def get_anonymous_user_id(self, username, course_id):
        """
        Get the anonymous user id from Xblock user service.

        Args:
            username(str): user's name entered by staff to get info.
            course_id(str): course id.

        Returns:
            A unique id for (user, course) pair
        """
        return self.runtime.service(self, 'user').get_anonymous_user_id(username, course_id)

    def is_user_state_service_available(self):
        """
        Check if the user state service is present in runtime.
        """
        try:
            self.runtime.service(self, 'user_state')
            return True
        except NoSuchServiceError:
            return False

    def get_user_state(self, username):
        """
        Get the student module state for the given username for current ORA block.

        Arguments:
            username(str): username against which the state is required in the current block.

        Returns:
            user state, if found, else empty dict
        """
        if self.is_user_state_service_available():
            user_state_service = self.runtime.service(self, 'user_state')
            return user_state_service.get_state_as_dict(username, str(self.location))  # pylint: disable=no-member
        return {}

    def should_use_user_state(self, upload_urls):
        """
        Return a boolean if the user state is used for additional data checks.

        User state is utilized when all of the following are true:
        1. user state service is available(which is only part of courseware)
        2. The waffle flag/switch is enabled
        3. the file upload is required or optional
        4. the file data from submission is missing information
        """
        return not any(upload_urls) \
            and self.is_user_state_service_available() \
            and self.user_state_upload_data_enabled \
            and self.file_upload_response

    def should_get_all_files_urls(self, upload_urls):
        """
        Returns a boolean to decide if all the file submitted by a learner in a block should be obtained.

        Following conditions should be true for boolean to be true:
        1. The waffle flag/switch is enabled
        2. the file upload is required or optional
        3. the file data from submission is missing information

        Arguments:
            upload_urls(list): A list of (file url, description, name) tuple, if info present, else empty list
        """
        return not any(upload_urls) \
            and self.is_fetch_all_urls_waffle_enabled \
            and self.file_upload_response

    def get_student_item_dict_from_username_or_email(self, username_or_email):
        """
        Get the item dict for a given username or email in the parent course of block.
        """
        anonymous_user_id = self.get_anonymous_user_id(username_or_email, self.course_id)
        return self.get_student_item_dict(anonymous_user_id=anonymous_user_id)

    def get_anonymous_user_id_from_xmodule_runtime(self):
        if hasattr(self, "xmodule_runtime"):
            return self.xmodule_runtime.anonymous_student_id  # pylint:disable=E1101
        return None

    def get_student_item_dict(self, anonymous_user_id=None):
        """Create a student_item_dict from our surrounding context.

        See also: submissions.api for details.

        Args:
            anonymous_user_id(str): A unique anonymous_user_id for (user, course) pair.
        Returns:
            (dict): The student item associated with this XBlock instance. This
                includes the student id, item id, and course id.
        """

        item_id = str(self.scope_ids.usage_id)

        # This is not the real way course_ids should work, but this is a
        # temporary expediency for LMS integration
        if hasattr(self, "xmodule_runtime"):
            course_id = self.course_id
            if anonymous_user_id:
                student_id = anonymous_user_id
            else:
                student_id = self.xmodule_runtime.anonymous_student_id  # pylint:disable=E1101
        else:
            course_id = "edX/Enchantment_101/April_1"
            if self.scope_ids.user_id is None:
                student_id = None
            else:
                student_id = str(self.scope_ids.user_id)

        student_item_dict = dict(
            student_id=student_id,
            item_id=item_id,
            course_id=course_id,
            item_type='openassessment'
        )
        return student_item_dict

    def add_javascript_files(self, fragment, item):
        """
        Add all the JavaScript files from a directory to the specified fragment
        """
        if pkg_resources.resource_isdir(__name__, item):
            for child_item in pkg_resources.resource_listdir(__name__, item):
                path = os.path.join(item, child_item)
                if not pkg_resources.resource_isdir(__name__, path):
                    fragment.add_javascript_url(self.runtime.local_resource_url(self, path))
        else:
            fragment.add_javascript_url(self.runtime.local_resource_url(self, item))

    @togglable_mobile_support
    def student_view(self, context=None):  # pylint: disable=unused-argument
        """The main view of OpenAssessmentBlock, displayed when viewing courses.

        The main view which displays the general layout for Open Ended
        Assessment Questions. The contents of the XBlock are determined
        dynamically based on the assessment workflow configured by the author.

        Args:
            context: Not used for this view.

        Returns:
            (Fragment): The HTML Fragment for this XBlock, which determines the
            general frame of the Open Ended Assessment Question.
        """
        # On page load, update the workflow status.
        # We need to do this here because peers may have graded us, in which
        # case we may have a score available.

        try:
            self.update_workflow_status()
        except AssessmentWorkflowError:
            # Log the exception, but continue loading the page
            logger.exception('An error occurred while updating the workflow on page load.')

        ui_models = self._create_ui_models()
        # All data we intend to pass to the front end.
        context_dict = {
            "title": self.title,
            "prompts": self.prompts,
            "prompts_type": self.prompts_type,
            "rubric_assessments": ui_models,
            "show_staff_area": self.is_course_staff and not self.in_studio_preview,
        }
        template = get_template("openassessmentblock/oa_base.html")
        return self._create_fragment(template, context_dict, initialize_js_func='OpenAssessmentBlock')

    def ora_blocks_listing_view(self, context=None):
        """This view is used in the Open Response Assessment tab in the LMS Instructor Dashboard
        to display all available course ORA blocks.

        Args:
            context: contains two items:
                "ora_items" - all course items with names and parents, example:
                    [{"parent_name": "Vertical name",
                      "name": "ORA Display Name",
                      "url_grade_available_responses": "/grade_available_responses_view",
                      "url_waiting_step_details": "/waiting_step_details_view",
                      "staff_assessment": false,
                      "parent_id": "vertical_block_id",
                      "url_base": "/student_view",
                      "id": "openassessment_block_id"
                     }, ...]
                "ora_item_view_enabled" - enabled LMS API endpoint to serve XBlock view or not

        Returns:
            (Fragment): The HTML Fragment for this XBlock.
        """
        ora_items = context.get('ora_items', []) if context else []
        ora_item_view_enabled = context.get('ora_item_view_enabled', False) if context else False
        context_dict = {
            "ora_items": json.dumps(ora_items),
            "ora_item_view_enabled": ora_item_view_enabled
        }

        template = get_template('openassessmentblock/instructor_dashboard/oa_listing.html')

        min_postfix = '.min' if settings.DEBUG else ''

        return self._create_fragment(
            template,
            context_dict,
            initialize_js_func='CourseOpenResponsesListingBlock',
            additional_css=["static/css/lib/backgrid/backgrid%s.css" % min_postfix],
            additional_js=["static/js/lib/backgrid/backgrid%s.js" % min_postfix],
            additional_js_context={
                "ENHANCED_STAFF_GRADER": self.is_enhanced_staff_grader_enabled,
                "ORA_GRADING_MICROFRONTEND_URL": getattr(settings, 'ORA_GRADING_MICROFRONTEND_URL', '')
            }
        )

    def grade_available_responses_view(self, context=None):  # pylint: disable=unused-argument
        """Grade Available Responses view.

        Auxiliary view which displays the staff grading area
        (used in the Open Response Assessment tab in the Instructor Dashboard of LMS)

        Args:
            context: Not used for this view.

        Returns:
            (Fragment): The HTML Fragment for this XBlock.
        """
        student_item = self.get_student_item_dict()
        staff_assessment_required = "staff-assessment" in self.assessment_steps

        context_dict = {
            "title": self.title,
            'staff_assessment_required': staff_assessment_required,
        }

        if staff_assessment_required:
            context_dict.update(
                self.get_staff_assessment_statistics_context(student_item["course_id"], student_item["item_id"])
            )

        template = get_template('openassessmentblock/instructor_dashboard/oa_grade_available_responses.html')

        return self._create_fragment(template, context_dict, initialize_js_func='StaffAssessmentBlock')

    def waiting_step_details_view(self, context=None):  # pylint: disable=unused-argument
        """
        Waiting Step Details view.

        Auxiliary view which displays a list of students "stuck" in the
        peer grading step waiting for a grade (used in the Open Response Assessment
        tab in the Instructor Dashboard of LMS).

        Args:
            context: Not used for this view.

        Returns:
            (Fragment): The HTML Fragment for this XBlock.
        """
        peer_assessment_required = "peer-assessment" in self.assessment_steps

        context_dict = {
            "title": self.title,
            "peer_assessment_required": peer_assessment_required,
        }

        if peer_assessment_required:
            context_dict['waiting_step_data_url'] = self.runtime.handler_url(
                self, "waiting_step_data",
            )

        template = get_template('openassessmentblock/instructor_dashboard/oa_waiting_step_details.html')

        return self._create_fragment(
            template,
            context_dict,
            initialize_js_func='WaitingStepDetailsBlock',
            additional_js_context=context_dict,
        )

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

    @property
    def is_admin(self):
        """
        Check whether the user has global staff permissions.

        Returns:
            bool
        """
        if hasattr(self, 'xmodule_runtime'):
            return getattr(self.xmodule_runtime, 'user_is_admin', False)  # pylint: disable=no-member
        return False

    @property
    def is_course_staff(self):
        """
        Check whether the user has course staff permissions for this XBlock.

        Returns:
            bool
        """
        if hasattr(self, 'xmodule_runtime'):
            return getattr(self.xmodule_runtime, 'user_is_staff', False)  # pylint: disable=no-member
        return False

    @property
    def is_beta_tester(self):
        """
        Check whether the user is a beta tester.

        Returns:
            bool
        """
        if hasattr(self, 'xmodule_runtime'):
            return getattr(self.xmodule_runtime, 'user_is_beta_tester', False)  # pylint: disable=no-member
        return False

    @property
    def in_studio_preview(self):
        """
        Check whether we are in Studio preview mode.

        Returns:
            bool

        """
        # When we're running in Studio Preview mode, the XBlock won't provide us with a user ID.
        # (Note that `self.xmodule_runtime` will still provide an anonymous
        # student ID, so we can't rely on that)
        return self.scope_ids.user_id is None

    @property
    def has_real_user(self):
        """
        Checks whether the runtime is tied to a real user

        Returns:
            bool
        """
        if hasattr(self, 'xmodule_runtime'):
            return self.xmodule_runtime.get_real_user is not None  # pylint: disable=no-member
        return False

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

        if not staff_assessment_required and self.staff_assessment_exists(self.submission_uuid):
            ui_models.append(UI_MODELS["staff-assessment"])

        ui_models.append(UI_MODELS["grade"])

        if self.leaderboard_show > 0 and not self.teams_enabled:
            ui_models.append(UI_MODELS["leaderboard"])

        return ui_models

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench.

        These scenarios are only intended to be used for Workbench XBlock
        Development.

        """
        return [
            (
                "OpenAssessmentBlock File Upload: Images",
                load('static/xml/file_upload_image_only.xml')
            ),
            (
                "OpenAssessmentBlock File Upload: PDF and Images",
                load('static/xml/file_upload_pdf_and_image.xml')
            ),
            (
                "OpenAssessmentBlock File Upload: Custom File Types",
                load('static/xml/file_upload_custom.xml')
            ),
            (
                "OpenAssessmentBlock File Upload: allow_file_upload compatibility",
                load('static/xml/file_upload_compat.xml')
            ),
            (
                "OpenAssessmentBlock Unicode",
                load('static/xml/unicode.xml')
            ),
            (
                "OpenAssessmentBlock Poverty Rubric",
                load('static/xml/poverty_rubric_example.xml')
            ),
            (
                "OpenAssessmentBlock Leaderboard",
                load('static/xml/leaderboard.xml')
            ),
            (
                "OpenAssessmentBlock Leaderboard with Custom File Type",
                load('static/xml/leaderboard_custom.xml')
            ),
            (
                "OpenAssessmentBlock (Peer Only) Rubric",
                load('static/xml/poverty_peer_only_example.xml')
            ),
            (
                "OpenAssessmentBlock (Self Only) Rubric",
                load('static/xml/poverty_self_only_example.xml')
            ),
            (
                "OpenAssessmentBlock Censorship Rubric",
                load('static/xml/censorship_rubric_example.xml')
            ),
            (
                "OpenAssessmentBlock Promptless Rubric",
                load('static/xml/promptless_rubric_example.xml')
            ),
        ]

    @classmethod
    def parse_xml(cls, node, runtime, keys, id_generator):
        """Instantiate XBlock object from runtime XML definition.

        Inherited by XBlock core.

        """
        config = parse_from_xml(node)
        block = runtime.construct_xblock_from_class(cls, keys)

        xblock_validator = validator(block, block._, strict_post_release=False)
        xblock_validator(
            create_rubric_dict(config['prompts'], config['rubric_criteria']),
            config['rubric_assessments'],
            submission_start=config['submission_start'],
            submission_due=config['submission_due'],
            leaderboard_show=config['leaderboard_show']
        )

        block.rubric_criteria = config['rubric_criteria']
        block.rubric_feedback_prompt = config['rubric_feedback_prompt']
        block.rubric_feedback_default_text = config['rubric_feedback_default_text']
        block.rubric_assessments = config['rubric_assessments']
        block.submission_start = config['submission_start']
        block.submission_due = config['submission_due']
        block.title = config['title']
        block.prompts = config['prompts']
        block.prompts_type = config['prompts_type']
        block.text_response = config['text_response']
        block.text_response_editor = config['text_response_editor']
        block.file_upload_response = config['file_upload_response']
        block.allow_file_upload = config['allow_file_upload']
        block.file_upload_type = config['file_upload_type']
        block.white_listed_file_types_string = config['white_listed_file_types']
        block.allow_multiple_files = config['allow_multiple_files']
        block.allow_latex = config['allow_latex']
        block.leaderboard_show = config['leaderboard_show']
        block.group_access = config['group_access']
        block.teams_enabled = config['teams_enabled']
        block.selected_teamset_id = config['selected_teamset_id']
        block.show_rubric_during_response = config['show_rubric_during_response']
        return block

    @property
    def _(self):
        i18nService = self.runtime.service(self, 'i18n')  # pylint: disable=invalid-name
        return i18nService.ugettext

    @property
    def prompts(self):
        """
        Return the prompts.

        Initially a block had a single prompt which was saved as a simple
        string in the prompt field. Now prompts are saved as a serialized
        list of dicts in the same field. If prompt field contains valid json,
        parse and return it. Otherwise, assume it is a simple string prompt
        and return it in a list of dict.

        Returns:
            list of dict
        """
        return create_prompts_list(self.prompt)

    @prompts.setter
    def prompts(self, value):
        """
        Serialize the prompts and save to prompt field.

        Args:
            value (list of dict): The prompts to set.
        """

        if value is None:
            self.prompt = None
        elif len(value) == 1:
            # For backwards compatibility. To be removed after all code
            # is migrated to use prompts property instead of prompt field.
            self.prompt = value[0]['description']
        else:
            self.prompt = json.dumps(value)

    @property
    def valid_assessments(self):
        """
        Return a list of assessment dictionaries that we recognize.
        This allows us to gracefully handle situations in which unrecognized
        assessment types are stored in the XBlock field (e.g. because
        we roll back code after releasing a feature).

        Returns:
            list

        """
        assessment_types = self.VALID_ASSESSMENT_TYPES
        if self.teams_enabled:
            assessment_types = self.VALID_ASSESSMENT_TYPES_FOR_TEAMS

        _valid_assessments = [
            asmnt for asmnt in self.rubric_assessments
            if asmnt.get('name') in assessment_types
        ]
        return update_assessments_format(copy.deepcopy(_valid_assessments))

    @property
    def assessment_steps(self):
        """
        Return a list of assessment steps by name.
        Also filter out assessments that have required set to false and do not
        contain a staff grade override.

        Returns:
            list

        """
        assessment_steps = []
        for assessment in self.valid_assessments:
            if assessment['name'] == 'staff-assessment' and assessment["required"] is False:
                if not self.staff_assessment_exists(self.submission_uuid):
                    continue
            assessment_steps.append(assessment['name'])
        return assessment_steps

    @lazy
    def rubric_criteria_with_labels(self):
        """
        Backwards compatibility: We used to treat "name" as both a user-facing label
        and a unique identifier for criteria and options.
        Now we treat "name" as a unique identifier, and we've added an additional "label"
        field that we display to the user.
        If criteria/options in the problem definition do NOT have a "label" field
        (because they were created before this change),
        we create a new label that has the same value as "name".

        The result of this call is cached, so it should NOT be used in a runtime
        that can modify the XBlock settings (in the LMS, settings are read-only).

        Returns:
            list of criteria dictionaries

        """
        criteria = copy.deepcopy(self.rubric_criteria)
        for criterion in criteria:
            if 'label' not in criterion:
                criterion['label'] = criterion['name']
            for option in criterion['options']:
                if 'label' not in option:
                    option['label'] = option['name']
        return criteria

    def render_assessment(self, path, context_dict=None):
        """Render an Assessment Module's HTML

        Given the name of an assessment module, find it in the list of
        configured modules, and ask for its rendered HTML.

        Args:
            path (str): The path to the template used to render this HTML
                section.
            context_dict (dict): A dictionary of context variables used to
                populate this HTML section.

        Returns:
            (Response): A Response Object with the generated HTML fragment. This
                is intended for AJAX calls to load dynamically into a larger
                document.
        """
        if not context_dict:
            context_dict = {}

        context_dict['text_response_editor'] = self.text_response_editor

        template = get_template(path)
        return Response(template.render(context_dict), content_type='application/html', charset='UTF-8')

    def add_xml_to_node(self, node):
        """
        Serialize the XBlock to XML for exporting.
        """
        serialize_content_to_xml(self, node)

    def render_error(self, error_msg):
        """
        Render an error message.

        Args:
            error_msg (unicode): The error message to display.

        Returns:
            Response: A response object with an HTML body.
        """
        context = {'error_msg': error_msg}
        template = get_template('openassessmentblock/oa_error.html')
        return Response(template.render(context), content_type='application/html', charset='UTF-8')

    def is_closed(self, step=None, course_staff=None):
        """
        Checks if the question is closed.

        Determines if the start date is in the future or the end date has
            passed.  Optionally limited to a particular step in the workflow.

        Start/due dates do NOT apply to course staff, since course staff may need to get to
        the peer grading step AFTER the submission deadline has passed.
        This may not be necessary when we implement a grading interface specifically for course staff.

        Keyword Arguments:
            step (str): The step in the workflow to check.  Options are:
                None: check whether the problem as a whole is open.
                "submission": check whether the submission section is open.
                "peer-assessment": check whether the peer-assessment section is open.
                "self-assessment": check whether the self-assessment section is open.

            course_staff (bool): Whether to treat the user as course staff (disable start/due dates).
                If not specified, default to the current user's status.

        Returns:
            tuple of the form (is_closed, reason, start_date, due_date), where
                is_closed (bool): indicates whether the step is closed.
                reason (str or None): specifies the reason the step is closed ("start" or "due")
                start_date (datetime): is the start date of the step/problem.
                due_date (datetime): is the due date of the step/problem.

        Examples:
            >>> is_closed()
            False, None, datetime.datetime(2014, 3, 27, 22, 7, 38, 788861),
            datetime.datetime(2015, 3, 27, 22, 7, 38, 788861)
            >>> is_closed(step="submission")
            True, "due", datetime.datetime(2014, 3, 27, 22, 7, 38, 788861),
            datetime.datetime(2015, 3, 27, 22, 7, 38, 788861)
            >>> is_closed(step="self-assessment")
            True, "start", datetime.datetime(2014, 3, 27, 22, 7, 38, 788861),
            datetime.datetime(2015, 3, 27, 22, 7, 38, 788861)

        """
        submission_range = (self.submission_start, self.submission_due)
        assessment_ranges = [
            (asmnt.get('start'), asmnt.get('due'))
            for asmnt in self.valid_assessments
        ]

        # Resolve unspecified dates and date strings to datetimes
        start, due, date_ranges = resolve_dates(
            self.start, self.due, [submission_range] + assessment_ranges, self._
        )

        open_range = (start, due)
        assessment_steps = self.assessment_steps
        if step == 'submission':
            open_range = date_ranges[0]
        elif step in assessment_steps:
            step_index = assessment_steps.index(step)
            open_range = date_ranges[1 + step_index]

        # Course staff always have access to the problem
        if course_staff is None:
            course_staff = self.is_course_staff
        if course_staff:
            return False, None, DISTANT_PAST, DISTANT_FUTURE

        if self.is_beta_tester:
            beta_start = self._adjust_start_date_for_beta_testers(open_range[0])
            open_range = (beta_start, open_range[1])

        # Check if we are in the open date range
        now = dt.datetime.utcnow().replace(tzinfo=pytz.utc)

        if now < open_range[0]:
            return True, "start", open_range[0], open_range[1]
        elif now >= open_range[1]:
            return True, "due", open_range[0], open_range[1]
        return False, None, open_range[0], open_range[1]

    def get_waiting_details(self, status_details):
        """
        Returns waiting status (boolean value) based on the given status_details.

        Args:
            status_details (dict): A dictionary containing the details of each
                assessment module status. This will contain keys such as
                "peer", "ai", and "staff", referring to dictionaries, which in
                turn will have the key "graded". If this key has a value set,
                these assessment modules have been graded.

        Returns:
            True if waiting for a grade from peer, ai, or staff assessment, else False.

        Examples:
            >>> now = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
            >>> status_details = {
            >>>     'peer': {
            >>>         'completed': None,
            >>>         'graded': now
            >>>     },
            >>>     'ai': {
            >>>         'completed': now,
            >>>         'graded': None
            >>>     }
            >>> }
            >>> self.get_waiting_details(status_details)
            True
        """
        steps = ["peer", "ai", "staff"]  # These are the steps that can be submitter-complete, but lack a grade
        for step in steps:
            if step in status_details and not status_details[step]["graded"]:
                return True
        return False

    def is_released(self, step=None):
        """
        Check if a question has been released.

        Keyword Arguments:
            step (str): The step in the workflow to check.
                None: check whether the problem as a whole is open.
                "submission": check whether the submission section is open.
                "peer-assessment": check whether the peer-assessment section is open.
                "self-assessment": check whether the self-assessment section is open.

        Returns:
            bool
        """
        # By default, assume that we're published, in case the runtime doesn't support publish date.
        if hasattr(self.runtime, 'modulestore'):
            is_published = self.runtime.modulestore.has_published_version(self)
        else:
            is_published = True
        try:
            is_closed, reason, __, __ = self.is_closed(step=step)  # pylint: disable=redeclared-assigned-name
        except DateValidationError:
            # Workaround so that studio_mixin workflow wil still work in the case that we have invalid dates
            is_closed = False
            reason = ''
        is_released = is_published and (not is_closed or reason == 'due')
        if self.start:
            is_released = is_released and dt.datetime.now(pytz.UTC) > parse_date_value(self.start, self._)
        return is_released

    def get_assessment_module(self, mixin_name):
        """
        Get a configured assessment module by name.

        Args:
            mixin_name (str): The name of the mixin (e.g. "self-assessment" or "peer-assessment")

        Returns:
            dict

        Example:
            >>> self.get_assessment_module('peer-assessment')
            {
                "name": "peer-assessment",
                "start": None,
                "due": None,
                "must_grade": 5,
                "must_be_graded_by": 3,
            }
        """
        for assessment in self.valid_assessments:
            if assessment["name"] == mixin_name:
                return assessment
        return None

    def publish_assessment_event(self, event_name, assessment, **kwargs):
        """
        Emit an analytics event for the peer assessment.

        Args:
            event_name (str): An identifier for this event type.
            assessment (dict): The serialized assessment model.

        Returns:
            None

        """
        parts_list = []
        for part in assessment["parts"]:
            # Some assessment parts do not include point values,
            # only written feedback.  In this case, the assessment
            # part won't have an associated option.
            option_dict = None
            if part["option"] is not None:
                option_dict = {
                    "name": part["option"]["name"],
                    "points": part["option"]["points"],
                }

            # All assessment parts are associated with criteria
            criterion_dict = {
                "name": part["criterion"]["name"],
                "points_possible": part["criterion"]["points_possible"]
            }

            parts_list.append({
                "option": option_dict,
                "criterion": criterion_dict,
                "feedback": part["feedback"]
            })

        event_data = {
            "feedback": assessment["feedback"],
            "rubric": {
                "content_hash": assessment["rubric"]["content_hash"],
            },
            "scorer_id": assessment["scorer_id"],
            "score_type": assessment["score_type"],
            "scored_at": assessment["scored_at"],
            "submission_uuid": assessment["submission_uuid"],
            "parts": parts_list
        }

        for key, value in kwargs.items():
            event_data[key] = value

        self.runtime.publish(
            self, event_name,
            event_data
        )

    @XBlock.json_handler
    def publish_event(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Publish the given data to an event.

        Expects key 'event_name' to be present in the data dictionary.
        """

        try:
            event_name = data['event_name']
        except KeyError:
            logger.exception("Could not find the name of the event to be triggered.")
            return {'success': False}

        # Remove the name so we don't publish as part of the data.
        del data['event_name']

        self.runtime.publish(self, event_name, data)
        return {'success': True}

    def get_real_user(self, anonymous_user_id):
        """
        Return the user associated with anonymous_user_id
        Args:
            anonymous_user_id (str): the anonymous user id of the user

        Returns: the user model for the user if it can be identified.
            If the xblock service to converts to a real user fails,
            returns None and logs the error.

        """
        if hasattr(self, "xmodule_runtime"):
            if self.xmodule_runtime.get_real_user is None:  # pylint: disable=no-member
                return None
            user = self.xmodule_runtime.get_real_user(anonymous_user_id)  # pylint: disable=no-member
            if user:
                return user
            logger.exception(
                "XBlock service could not find user for anonymous_user_id '%s'", anonymous_user_id
            )
        return None

    def get_username(self, anonymous_user_id):
        """
        Return the username of the user associated with anonymous_user_id
        Args:
            anonymous_user_id (str): the anonymous user id of the user

        Returns: the username if it can be identified.

        """
        user = self.get_real_user(anonymous_user_id)
        if user:
            return user.username
        return None

    def _adjust_start_date_for_beta_testers(self, start):
        """
        Returns the start date for a Beta tester.
        """
        if hasattr(self, "xmodule_runtime"):
            days_early_for_beta = getattr(self.xmodule_runtime, 'days_early_for_beta', 0)  # pylint: disable=no-member
            if days_early_for_beta is not None:
                delta = dt.timedelta(days_early_for_beta)
                effective = start - delta
                return effective

        return start

    def get_xblock_id(self):
        """
        Returns the xblock id
        """
        return str(self.scope_ids.usage_id)

    def _clean_data(self, data):
        cleaner = Cleaner(tags=[], strip=True)
        cleaned_text = " ".join(re.split(r"\s+", cleaner.clean(data), flags=re.UNICODE)).strip()
        return cleaned_text

    def index_dictionary(self):
        """
        Return dictionary prepared with module content and type for indexing.
        """

        # return key/value fields in a Python dict object
        # values may be numeric / string or dict
        # default implementation is an empty dict
        xblock_body = super().index_dictionary()

        # Check whether there is only one prompt or more than one
        # If there is single prompt, self.prompt would be simply a string
        # otherwise self.prompt would have json embedded in the string.
        try:
            prompt = {
                f"prompt_{prompt_i}": self._clean_data(prompt.get("description", ""))
                for prompt_i, prompt in enumerate(json.loads(self.prompt))
            }
        except ValueError:
            prompt = {
                "prompt": self._clean_data(self.prompt)
            }

        content = {
            "display_name": self.display_name,
            "title": self.title,
            **prompt
        }

        if "content" in xblock_body:
            xblock_body["content"].update(content)
        else:
            xblock_body["content"] = content

        xblock_body["content_type"] = "ORA"

        return xblock_body
