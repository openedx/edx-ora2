"""An XBlock where students can read a question and compose their response"""

import datetime as dt
import logging
import pkg_resources
import copy

import pytz

from django.template.context import Context
from django.template.loader import get_template
from webob import Response
from lazy import lazy

from xblock.core import XBlock
from xblock.fields import List, Scope, String, Boolean, Integer
from xblock.fragment import Fragment
from openassessment.xblock.grade_mixin import GradeMixin
from openassessment.xblock.leaderboard_mixin import LeaderboardMixin
from openassessment.xblock.defaults import * # pylint: disable=wildcard-import, unused-wildcard-import
from openassessment.xblock.message_mixin import MessageMixin
from openassessment.xblock.peer_assessment_mixin import PeerAssessmentMixin
from openassessment.xblock.lms_mixin import LmsCompatibilityMixin
from openassessment.xblock.self_assessment_mixin import SelfAssessmentMixin
from openassessment.xblock.submission_mixin import SubmissionMixin
from openassessment.xblock.studio_mixin import StudioMixin
from openassessment.xblock.xml import parse_from_xml, serialize_content_to_xml
from openassessment.xblock.staff_info_mixin import StaffInfoMixin
from openassessment.xblock.workflow_mixin import WorkflowMixin
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.student_training_mixin import StudentTrainingMixin
from openassessment.xblock.validation import validator
from openassessment.xblock.resolve_dates import resolve_dates, DISTANT_PAST, DISTANT_FUTURE
from openassessment.xblock.data_conversion import create_rubric_dict


logger = logging.getLogger(__name__)


UI_MODELS = {
    "submission": {
        "name": "submission",
        "class_id": "openassessment__response",
        "navigation_text": "Your response to this assignment",
        "title": "Your Response"
    },
    "student-training": {
        "name": "student-training",
        "class_id": "openassessment__student-training",
        "navigation_text": "Learn to assess responses",
        "title": "Learn to Assess"
    },
    "peer-assessment": {
        "name": "peer-assessment",
        "class_id": "openassessment__peer-assessment",
        "navigation_text": "Your assessment(s) of peer responses",
        "title": "Assess Peers' Responses"
    },
    "self-assessment": {
        "name": "self-assessment",
        "class_id": "openassessment__self-assessment",
        "navigation_text": "Your assessment of your response",
        "title": "Assess Your Response"
    },
    "grade": {
        "name": "grade",
        "class_id": "openassessment__grade",
        "navigation_text": "Your grade for this assignment",
        "title": "Your Grade:"
    },
     "leaderboard": {
        "name": "leaderboard",
        "class_id": "openassessment__leaderboard",
        "navigation_text": "A leaderboard of the top submissions",
        "title": "Leaderboard"
    }
}

VALID_ASSESSMENT_TYPES = [
    "student-training",
    "example-based-assessment",
    "peer-assessment",
    "self-assessment",
]


def load(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")

@XBlock.needs("i18n")
@XBlock.needs("user")
class OpenAssessmentBlock(
    MessageMixin,
    SubmissionMixin,
    PeerAssessmentMixin,
    SelfAssessmentMixin,
    StudioMixin,
    GradeMixin,
    LeaderboardMixin,
    StaffInfoMixin,
    WorkflowMixin,
    StudentTrainingMixin,
    LmsCompatibilityMixin,
    XBlock,
):
    """Displays a prompt and provides an area where students can compose a response."""

    submission_start = String(
        default=DEFAULT_START, scope=Scope.settings,
        help="ISO-8601 formatted string representing the submission start date."
    )

    submission_due = String(
        default=DEFAULT_DUE, scope=Scope.settings,
        help="ISO-8601 formatted string representing the submission due date."
    )

    allow_file_upload = Boolean(
        default=False,
        scope=Scope.content,
        help="File upload allowed with submission."
    )

    allow_latex = Boolean(
        default=False,
        scope=Scope.settings,
        help="Latex rendering allowed with submission."
    )

    title = String(
        default="",
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
        help="A prompt to display to a student (plain text)."
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

    course_id = String(
        default=u"TestCourse",
        scope=Scope.content,
        help="The course_id associated with this prompt (until we can get it from runtime)."
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
        default=u"",
        scope=Scope.user_state,
        help="Saved response submission for the current user."
    )

    no_peers = Boolean(
        default=False,
        scope=Scope.user_state,
        help="Indicates whether or not there are peers to grade."
    )

    @property
    def course_id(self):
        return self._serialize_opaque_key(self.xmodule_runtime.course_id)  # pylint:disable=E1101

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

    def get_student_item_dict(self, anonymous_user_id=None):
        """Create a student_item_dict from our surrounding context.

        See also: submissions.api for details.

        Args:
            anonymous_user_id(str): A unique anonymous_user_id for (user, course) pair.
        Returns:
            (dict): The student item associated with this XBlock instance. This
                includes the student id, item id, and course id.
        """

        item_id = self._serialize_opaque_key(self.scope_ids.usage_id)

        # This is not the real way course_ids should work, but this is a
        # temporary expediency for LMS integration
        if hasattr(self, "xmodule_runtime"):
            course_id = self.course_id  # pylint:disable=E1101
            if anonymous_user_id:
                student_id = anonymous_user_id
            else:
                student_id = self.xmodule_runtime.anonymous_student_id  # pylint:disable=E1101
        else:
            course_id = "edX/Enchantment_101/April_1"
            if self.scope_ids.user_id is None:
                student_id = None
            else:
                student_id = unicode(self.scope_ids.user_id)

        student_item_dict = dict(
            student_id=student_id,
            item_id=item_id,
            course_id=course_id,
            item_type='openassessment'
        )
        return student_item_dict

    def student_view(self, context=None):
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
            "question": self.prompt,
            "rubric_assessments": ui_models,
            "show_staff_debug_info": self.is_course_staff and not self.in_studio_preview,
        }
        template = get_template("openassessmentblock/oa_base.html")
        context = Context(context_dict)
        frag = Fragment(template.render(context))

        i18n_service = self.runtime.service(self, 'i18n')
        if hasattr(i18n_service, 'get_language_bidi') and i18n_service.get_language_bidi():
            frag.add_css(load("static/css/openassessment-rtl.css"))
        else:
            frag.add_css(load("static/css/openassessment-ltr.css"))

        frag.add_javascript(load("static/js/openassessment-lms.min.js"))
        frag.initialize_js('OpenAssessmentBlock')
        return frag


    @property
    def is_admin(self):
        """
        Check whether the user has global staff permissions.

        Returns:
            bool
        """
        if hasattr(self, 'xmodule_runtime'):
            return getattr(self.xmodule_runtime, 'user_is_admin', False)
        else:
            return False

    @property
    def is_course_staff(self):
        """
        Check whether the user has course staff permissions for this XBlock.

        Returns:
            bool
        """
        if hasattr(self, 'xmodule_runtime'):
            return getattr(self.xmodule_runtime, 'user_is_staff', False)
        else:
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

    def _create_ui_models(self):
        """Combine UI attributes and XBlock configuration into a UI model.

        This method takes all configuration for this XBlock instance and appends
        UI attributes to create a UI Model for rendering all assessment modules.
        This allows a clean separation of static UI attributes from persistent
        XBlock configuration.

        """
        ui_models = [UI_MODELS["submission"]]
        for assessment in self.valid_assessments:
            ui_model = UI_MODELS.get(assessment["name"])
            if ui_model:
                ui_models.append(dict(assessment, **ui_model))
        ui_models.append(UI_MODELS["grade"])

        if self.leaderboard_show > 0:
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
                "OpenAssessmentBlock Unicode",
                load('static/xml/unicode.xml')
            ),
            (
                "OpenAssessmentBlock Example Based Rubric",
                load('static/xml/example_based_example.xml')
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
            create_rubric_dict(config['prompt'], config['rubric_criteria']),
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
        block.prompt = config['prompt']
        block.allow_file_upload = config['allow_file_upload']
        block.allow_latex = config['allow_latex']
        block.leaderboard_show = config['leaderboard_show']

        return block

    @property
    def _(self):
        i18nService = self.runtime.service(self, 'i18n')
        return i18nService.ugettext

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
        return [
            asmnt for asmnt in self.rubric_assessments
            if asmnt.get('name') in VALID_ASSESSMENT_TYPES
        ]

    @property
    def assessment_steps(self):
        return [asmnt['name'] for asmnt in self.valid_assessments]

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

        template = get_template(path)
        context = Context(context_dict)
        return Response(template.render(context), content_type='application/html', charset='UTF-8')

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
        context = Context({'error_msg': error_msg})
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
            False, None, datetime.datetime(2014, 3, 27, 22, 7, 38, 788861), datetime.datetime(2015, 3, 27, 22, 7, 38, 788861)
            >>> is_closed(step="submission")
            True, "due", datetime.datetime(2014, 3, 27, 22, 7, 38, 788861), datetime.datetime(2015, 3, 27, 22, 7, 38, 788861)
            >>> is_closed(step="self-assessment")
            True, "start", datetime.datetime(2014, 3, 27, 22, 7, 38, 788861), datetime.datetime(2015, 3, 27, 22, 7, 38, 788861)

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

        # Check if we are in the open date range
        now = dt.datetime.utcnow().replace(tzinfo=pytz.utc)

        if now < open_range[0]:
            return True, "start", open_range[0], open_range[1]
        elif now >= open_range[1]:
            return True, "due", open_range[0], open_range[1]
        else:
            return False, None, open_range[0], open_range[1]

    def get_waiting_details(self, status_details):
        """
        Returns the specific waiting status based on the given status_details.
        This status can currently be peer, example-based, or both. This is
        determined by checking that status details to see if all assessment
        modules have been graded.

        Args:
            status_details (dict): A dictionary containing the details of each
                assessment module status. This will contain keys such as
                "peer" and "ai", referring to dictionaries, which in turn will
                have the key "graded". If this key has a value set, these
                assessment modules have been graded.

        Returns:
            A string of "peer", "exampled-based", or "all" to indicate which
            assessment modules in the workflow are waiting on assessments.
            Returns None if no module is waiting on an assessment.

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
            "peer"
        """
        waiting = None
        peer_waiting = "peer" in status_details and not status_details["peer"]["graded"]
        ai_waiting = "ai" in status_details and not status_details["ai"]["graded"]
        if peer_waiting and ai_waiting:
            waiting = "all"
        elif peer_waiting:
            waiting = "peer"
        elif ai_waiting:
            waiting = "example-based"
        return waiting

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
        is_closed, reason, __, __ = self.is_closed(step=step)
        return is_published and (not is_closed or reason == 'due')

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

    def publish_assessment_event(self, event_name, assessment):
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

        self.runtime.publish(
            self, event_name,
            {
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
        )

    def _serialize_opaque_key(self, key):
        """
        Gracefully handle opaque keys, both before and after the transition.
        https://github.com/edx/edx-platform/wiki/Opaque-Keys

        Currently uses `to_deprecated_string()` to ensure that new keys
        are backwards-compatible with keys we store in ORA2 database models.

        Args:
            key (unicode or OpaqueKey subclass): The key to serialize.

        Returns:
            unicode

        """
        if hasattr(key, 'to_deprecated_string'):
            return key.to_deprecated_string()
        else:
            return unicode(key)

    def get_username(self, anonymous_user_id):
        if hasattr(self, "xmodule_runtime"):
            return self.xmodule_runtime.get_real_user(anonymous_user_id).username
