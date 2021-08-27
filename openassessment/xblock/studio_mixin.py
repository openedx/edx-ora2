"""
Studio editing view for OpenAssessment XBlock.
"""


import copy
import logging
from uuid import uuid4

from django.template.loader import get_template
from django.utils.translation import ugettext_lazy

from voluptuous import MultipleInvalid
from xblock.fields import List, Scope
from xblock.core import XBlock
from web_fragments.fragment import Fragment
from openassessment.xblock.data_conversion import (
    create_rubric_dict,
    make_django_template_key,
    update_assessments_format
)
from openassessment.xblock.defaults import DEFAULT_EDITOR_ASSESSMENTS_ORDER, DEFAULT_RUBRIC_FEEDBACK_TEXT
from openassessment.xblock.resolve_dates import resolve_dates, parse_date_value, DateValidationError, InvalidDateFormat
from openassessment.xblock.schema import EDITOR_UPDATE_SCHEMA
from openassessment.xblock.validation import validator
from openassessment.xblock.editor_config import AVAILABLE_EDITORS
from openassessment.xblock.load_static import LoadStatic

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class StudioMixin:
    """
    Studio editing view for OpenAssessment XBlock.
    """

    DEFAULT_CRITERIA = [
        {
            'label': '',
            'options': [
                {
                    'label': ''
                },
            ]
        }
    ]

    NECESSITY_OPTIONS = {
        "required": ugettext_lazy("Required"),
        "optional": ugettext_lazy("Optional"),
        "": ugettext_lazy("None")
    }

    # Build editor options from AVAILABLE_EDITORS
    AVAILABLE_EDITOR_OPTIONS = {
        key: val.get('display_name', key) for key, val in AVAILABLE_EDITORS.items()
    }

    STUDIO_EDITING_TEMPLATE = 'openassessmentblock/edit/oa_edit.html'

    BASE_EDITOR_ASSESSMENTS_ORDER = copy.deepcopy(DEFAULT_EDITOR_ASSESSMENTS_ORDER)

    # Since the XBlock problem definition contains only assessment
    # modules that are enabled, we need to keep track of the order
    # that the user left assessments in the editor, including
    # the ones that were disabled.  This allows us to keep the order
    # that the user specified.
    editor_assessments_order = List(
        default=DEFAULT_EDITOR_ASSESSMENTS_ORDER,
        scope=Scope.content,
        help="The order to display assessments in the editor."
    )

    def studio_view(self, context=None):  # pylint: disable=unused-argument
        """
        Render the OpenAssessment XBlock for editing in Studio.

        Args:
            context: Not actively used for this view.

        Returns:
            (Fragment): An HTML fragment for editing the configuration of this XBlock.
        """
        rendered_template = get_template(
            self.STUDIO_EDITING_TEMPLATE
        ).render(self.editor_context())
        fragment = Fragment(rendered_template)

        fragment.add_javascript_url(LoadStatic.get_url('openassessment-studio.js'))

        js_context_dict = {
            "ALLOWED_IMAGE_EXTENSIONS": self.ALLOWED_IMAGE_EXTENSIONS,
            "ALLOWED_FILE_EXTENSIONS": self.ALLOWED_FILE_EXTENSIONS,
            "FILE_EXT_BLACK_LIST": self.FILE_EXT_BLACK_LIST,
        }
        fragment.initialize_js('OpenAssessmentEditor', js_context_dict)
        return fragment

    def editor_context(self):
        """
        Update the XBlock's XML.

        Returns:
            dict with keys
                'rubric' (unicode), 'prompt' (unicode), 'title' (unicode),
                'submission_start' (unicode),  'submission_due' (unicode),
                'assessments (dict)

        """
        # In the authoring GUI, date and time fields should never be null.
        # Therefore, we need to resolve all "default" dates to datetime objects
        # before displaying them in the editor.
        try:
            __, __, date_ranges = resolve_dates(  # pylint: disable=redeclared-assigned-name
                self.start, self.due,
                [
                    (self.submission_start, self.submission_due)
                ] + [
                    (asmnt.get('start'), asmnt.get('due'))
                    for asmnt in self.valid_assessments
                ],
                self._
            )
        except (DateValidationError, InvalidDateFormat):
            # If the dates are somehow invalid, we still want users to be able to edit the ORA,
            # so just present the dates as they are.
            def _parse_date_safe(date):
                try:
                    return parse_date_value(date, self._)
                except InvalidDateFormat:
                    return ''

            date_ranges = [
                (_parse_date_safe(self.submission_start), _parse_date_safe(self.submission_due))
            ] + [
                (_parse_date_safe(asmnt.get('start')), _parse_date_safe(asmnt.get('due')))
                for asmnt in self.valid_assessments
            ]

        submission_start, submission_due = date_ranges[0]
        assessments = self._assessments_editor_context(date_ranges[1:])
        self.editor_assessments_order = self._editor_assessments_order_context()

        # Every rubric requires one criterion. If there is no criteria
        # configured for the XBlock, return one empty default criterion, with
        # an empty default option.
        criteria = copy.deepcopy(self.rubric_criteria_with_labels)
        if not criteria:
            criteria = self.DEFAULT_CRITERIA

        # To maintain backwards compatibility, if there is no
        # feedback_default_text configured for the xblock, use the default text
        feedback_default_text = copy.deepcopy(self.rubric_feedback_default_text)
        if not feedback_default_text:
            feedback_default_text = DEFAULT_RUBRIC_FEEDBACK_TEXT
        course_id = self.location.course_key if hasattr(self, 'location') else None

        # If allowed file types haven't been explicitly set, load from a preset
        white_listed_file_types = self.get_allowed_file_types_or_preset()
        white_listed_file_types_string = ','.join(white_listed_file_types) if white_listed_file_types else ''

        # If rubric reuse is enabled, include information about the other ORAs in this course
        rubric_reuse_data = {}
        if self.is_rubric_reuse_enabled:
            rubric_reuse_data = self.get_other_ora_blocks_for_rubric_editor_context()

        return {
            'prompts': self.prompts,
            'prompts_type': self.prompts_type,
            'title': self.title,
            'submission_due': submission_due,
            'submission_start': submission_start,
            'assessments': assessments,
            'criteria': criteria,
            'feedbackprompt': self.rubric_feedback_prompt,
            'feedback_default_text': feedback_default_text,
            'text_response': self.text_response if self.text_response else '',
            'text_response_editor': self.text_response_editor if self.text_response_editor else 'text',
            'file_upload_response': self.file_upload_response if self.file_upload_response else '',
            'necessity_options': self.NECESSITY_OPTIONS,
            'available_editor_options': self.AVAILABLE_EDITOR_OPTIONS,
            'file_upload_type': self.file_upload_type,
            'allow_multiple_files': self.allow_multiple_files,
            'white_listed_file_types': white_listed_file_types_string,
            'allow_latex': self.allow_latex,
            'leaderboard_show': self.leaderboard_show,
            'editor_assessments_order': [
                make_django_template_key(asmnt)
                for asmnt in self.editor_assessments_order
            ],
            'teams_feature_enabled': self.team_submissions_enabled,
            'teams_enabled': self.teams_enabled,
            'base_asset_url': self._get_base_url_path_for_course_assets(course_id),
            'is_released': self.is_released(),
            'teamsets': self.get_teamsets(course_id),
            'selected_teamset_id': self.selected_teamset_id,
            'show_rubric_during_response': self.show_rubric_during_response,
            'rubric_reuse_enabled': self.is_rubric_reuse_enabled,
            'rubric_reuse_data': rubric_reuse_data,
            'block_location': str(self.location),
        }

    @XBlock.json_handler
    def update_editor_context(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Update the XBlock's configuration.

        Args:
            data (dict): Data from the request; should have the format described
            in the editor schema.

        Keyword Arguments:
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
            return {'success': False, 'msg': self._('Error updating XBlock configuration')}

        # Check that the editor assessment order contains all the assessments.
        current_order = set(data['editor_assessments_order'])
        if set(DEFAULT_EDITOR_ASSESSMENTS_ORDER) != current_order:
            # Backwards compatibility: "staff-assessment" may not be present.
            # If that is the only problem with this data, just add it manually and continue.
            if set(DEFAULT_EDITOR_ASSESSMENTS_ORDER) == current_order | {'staff-assessment'}:
                data['editor_assessments_order'].append('staff-assessment')
                logger.info('Backwards compatibility: editor_assessments_order now contains staff-assessment')
            else:
                logger.exception('editor_assessments_order does not contain all expected assessment types')
                return {'success': False, 'msg': self._('Error updating XBlock configuration')}

        if not data['text_response'] and not data['file_upload_response']:
            return {
                'success': False,
                'msg': self._("Error: Text Response and File Upload Response cannot both be disabled")
            }
        if not data['text_response'] and data['file_upload_response'] == 'optional':
            return {'success': False,
                    'msg': self._("Error: When Text Response is disabled, File Upload Response must be Required")}
        if not data['file_upload_response'] and data['text_response'] == 'optional':
            return {'success': False,
                    'msg': self._("Error: When File Upload Response is disabled, Text Response must be Required")}

        # Backwards compatibility: We used to treat "name" as both a user-facing label
        # and a unique identifier for criteria and options.
        # Now we treat "name" as a unique identifier, and we've added an additional "label"
        # field that we display to the user.
        # If the JavaScript editor sends us a criterion or option without a "name"
        # field, we should assign it a unique identifier.
        for criterion in data['criteria']:
            if 'name' not in criterion:
                criterion['name'] = uuid4().hex
            for option in criterion['options']:
                if 'name' not in option:
                    option['name'] = uuid4().hex

        xblock_validator = validator(self, self._)
        success, msg = xblock_validator(
            create_rubric_dict(data['prompts'], data['criteria']),
            data['assessments'],
            submission_start=data['submission_start'],
            submission_due=data['submission_due'],
            leaderboard_show=data['leaderboard_show']
        )
        if not success:
            return {'success': False, 'msg': self._('Validation error: {error}').format(error=msg)}

        # At this point, all the input data has been validated,
        # so we can safely modify the XBlock fields.
        self.title = data['title']
        self.display_name = data['title']
        self.prompts = data['prompts']
        self.prompts_type = data['prompts_type']
        self.rubric_criteria = data['criteria']
        self.rubric_assessments = data['assessments']
        self.editor_assessments_order = data['editor_assessments_order']
        self.rubric_feedback_prompt = data['feedback_prompt']
        self.rubric_feedback_default_text = data['feedback_default_text']
        self.submission_start = data['submission_start']
        self.submission_due = data['submission_due']
        self.text_response = data['text_response']
        self.text_response_editor = data['text_response_editor']
        self.file_upload_response = data['file_upload_response']
        if data['file_upload_response']:
            self.file_upload_type = data['file_upload_type']
            self.white_listed_file_types_string = data['white_listed_file_types']
        else:
            self.file_upload_type = None
            self.white_listed_file_types_string = None
        self.allow_multiple_files = bool(data['allow_multiple_files'])
        self.allow_latex = bool(data['allow_latex'])
        self.leaderboard_show = data['leaderboard_show']
        self.teams_enabled = bool(data.get('teams_enabled', False))
        self.selected_teamset_id = data.get('selected_teamset_id', '')
        self.show_rubric_during_response = data.get('show_rubric_during_response', False)

        return {'success': True, 'msg': self._('Successfully updated OpenAssessment XBlock')}

    @XBlock.json_handler
    def check_released(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Check whether the problem has been released.

        Args:
            data (dict): Not used

        Keyword Arguments:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool), 'message' (unicode), and 'is_released' (bool)
        """
        # There aren't currently any server-side error conditions we report to the client,
        # but we send success/msg values anyway for consistency with other handlers.
        return {
            'success': True, 'msg': '',
            'is_released': self.is_released()
        }

    def _assessments_editor_context(self, assessment_dates):
        """
        Transform the rubric assessments list into the context
        we will pass to the Django template.

        Args:
            assessment_dates: List of assessment date ranges (tuples of start/end datetimes).

        Returns:
            dict

        """
        assessments = {}
        for asmnt, date_range in zip(self.rubric_assessments, assessment_dates):
            # Django Templates cannot handle dict keys with dashes, so we'll convert
            # the dashes to underscores.
            template_name = make_django_template_key(asmnt['name'])
            assessments[template_name] = copy.deepcopy(asmnt)
            assessments[template_name]['start'] = date_range[0]
            assessments[template_name]['due'] = date_range[1]

        # In addition to the data in the student training assessment, we need to include two additional
        # pieces of information: a blank context to render the empty template with, and the criteria
        # for each example (so we don't have any complicated logic within the template). Though this
        # could be accomplished within the template, we are opting to remove logic from the template.
        student_training_module = self.get_assessment_module('student-training')

        student_training_template = {
            'answer': {
                'parts': [
                    {'text': ''} for _ in self.prompts
                ]
            }
        }
        criteria_list = copy.deepcopy(self.rubric_criteria_with_labels)
        for criterion in criteria_list:
            criterion['option_selected'] = ""
        student_training_template['criteria'] = criteria_list

        if student_training_module:
            student_training_module = update_assessments_format([student_training_module])[0]
            example_list = []
            # Adds each example to a modified version of the student training module dictionary.
            for example in student_training_module['examples']:
                criteria_list = copy.deepcopy(self.rubric_criteria_with_labels)
                # Equivalent to a Join Query, this adds the selected option to the Criterion's dictionary, so that
                # it can be easily referenced in the template without searching through the selected options.
                for criterion in criteria_list:
                    for option_selected in example['options_selected']:
                        if option_selected['criterion'] == criterion['name']:
                            criterion['option_selected'] = option_selected['option']
                example_list.append({
                    'answer': example['answer'],
                    'criteria': criteria_list,
                })
            assessments['training'] = {'examples': example_list, 'template': student_training_template}
        # If we don't have student training enabled, we still need to render a single (empty, or default) example
        else:
            assessments['training'] = {'examples': [student_training_template], 'template': student_training_template}

        return assessments

    def _editor_assessments_order_context(self):
        """
        Create a list of assessment names in the order
        the user last set in the editor, including
        assessments that are not currently enabled.

        Returns:
            list of assessment names

        """
        # Start with the default order, to pick up any assessment types that have been added
        # since the user last saved their ordering.
        effective_order = copy.deepcopy(self.BASE_EDITOR_ASSESSMENTS_ORDER)

        # Account for changes the user has made to the default order
        user_order = copy.deepcopy(self.editor_assessments_order)
        effective_order = self._subset_in_relative_order(effective_order, user_order)

        # Account for inconsistencies between the user's order and the problems
        # that are currently enabled in the problem (These cannot be changed)
        enabled_assessments = [asmnt['name'] for asmnt in self.valid_assessments]
        enabled_ordered_assessments = [
            assessment for assessment in enabled_assessments if assessment in user_order
        ]
        effective_order = self._subset_in_relative_order(effective_order, enabled_ordered_assessments)

        return effective_order

    def _subset_in_relative_order(self, superset, subset):
        """
        Returns a copy of superset, with entries that appear in subset being reordered to match
        their relative ordering in subset.
        """
        superset_indices = [superset.index(item) for item in subset]
        sorted_superset_indices = sorted(superset_indices)
        if superset_indices != sorted_superset_indices:
            for index, superset_index in enumerate(sorted_superset_indices):
                superset[superset_index] = subset[index]
        return superset

    def _get_base_url_path_for_course_assets(self, course_key):
        """
        Returns base url path for course assets
        """
        if course_key is None:
            return None

        placeholder_id = uuid4().hex
        # create a dummy asset location with a fake but unique name. strip off the name, and return it
        url_path = str(course_key.make_asset_key('asset', placeholder_id).for_branch(None))
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        return url_path.replace(placeholder_id, '')

    def get_team_configuration(self, course_id):
        """
        Returns a dict with team configuration settings.
        """
        configuration_service = self.runtime.service(self, 'teams_configuration')
        team_configuration = configuration_service.get_teams_configuration(course_id)
        if not team_configuration:
            return None
        return team_configuration

    def get_teamsets(self, course_id):
        """
        Wrapper around get_team_configuration that returns team names only for display
        """
        team_configuration = self.get_team_configuration(course_id)
        if not team_configuration:
            return None
        return team_configuration.teamsets
