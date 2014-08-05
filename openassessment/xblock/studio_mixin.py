"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import copy
import logging
from django.template import Context
from django.template.loader import get_template
from voluptuous import MultipleInvalid
from xblock.core import XBlock
from xblock.fields import List, Scope
from xblock.fragment import Fragment
from openassessment.xblock.defaults import DEFAULT_EDITOR_ASSESSMENTS_ORDER, DEFAULT_RUBRIC_FEEDBACK_TEXT
from openassessment.xblock.validation import validator
from openassessment.xblock.data_conversion import create_rubric_dict, make_django_template_key
from openassessment.xblock.schema import EDITOR_UPDATE_SCHEMA
from openassessment.xblock.resolve_dates import resolve_dates
from openassessment.xblock.xml import serialize_examples_to_xml_str, parse_examples_from_xml_str
from xml import UpdateFromXmlError

logger = logging.getLogger(__name__)


class StudioMixin(object):
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

    def studio_view(self, context=None):
        """
        Render the OpenAssessment XBlock for editing in Studio.

        Args:
            context: Not actively used for this view.

        Returns:
            (Fragment): An HTML fragment for editing the configuration of this XBlock.
        """
        rendered_template = get_template(
            'openassessmentblock/edit/oa_edit.html'
        ).render(Context(self.editor_context()))
        frag = Fragment(rendered_template)
        frag.add_javascript(pkg_resources.resource_string(__name__, "static/js/openassessment-studio.min.js"))
        frag.initialize_js('OpenAssessmentEditor')
        return frag

    def editor_context(self):
        """
        Update the XBlock's XML.

        Args:
            data (dict): Data from the request; should have a value for the key 'xml'
                containing the XML for this XBlock.

        Keyword Arguments:
            suffix (str): Not used

        Returns:
            dict with keys
                'rubric' (unicode), 'prompt' (unicode), 'title' (unicode),
                'submission_start' (unicode),  'submission_due' (unicode),
                'assessments (dict)

        """
        # In the authoring GUI, date and time fields should never be null.
        # Therefore, we need to resolve all "default" dates to datetime objects
        # before displaying them in the editor.
        __, __, date_ranges = resolve_dates(
            self.start, self.due,
            [(self.submission_start, self.submission_due)] +
            [(asmnt.get('start'), asmnt.get('due')) for asmnt in self.valid_assessments],
            self._
        )

        submission_start, submission_due = date_ranges[0]
        assessments = self._assessments_editor_context(date_ranges[1:])
        editor_assessments_order = self._editor_assessments_order_context()

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

        track_changes = copy.deepcopy(self.track_changes)
        if not track_changes:
            track_changes = ''

        return {
            'prompt': self.prompt,
            'title': self.title,
            'submission_due': submission_due,
            'submission_start': submission_start,
            'assessments': assessments,
            'criteria': criteria,
            'track_changes': track_changes,
            'feedbackprompt': self.rubric_feedback_prompt,
            'feedback_default_text': feedback_default_text,
            'allow_file_upload': self.allow_file_upload,
            'allow_latex': self.allow_latex,
            'leaderboard_show': self.leaderboard_show,
            'editor_assessments_order': [
                make_django_template_key(asmnt)
                for asmnt in editor_assessments_order
            ],
        }

    @XBlock.json_handler
    def update_editor_context(self, data, suffix=''):
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

        # Check that the editor assessment order contains all the assessments.  We are more flexible on example-based.
        if set(DEFAULT_EDITOR_ASSESSMENTS_ORDER) != (set(data['editor_assessments_order']) - {'example-based-assessment'}):
            logger.exception('editor_assessments_order does not contain all expected assessment types')
            return {'success': False, 'msg': self._('Error updating XBlock configuration')}

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

        # If example based assessment is enabled, we replace it's xml definition with the dictionary
        # definition we expect for validation and storing.
        for assessment in data['assessments']:
            if assessment['name'] == 'example-based-assessment':
                try:
                    assessment['examples'] = parse_examples_from_xml_str(assessment['examples_xml'])
                except UpdateFromXmlError:
                    return {'success': False, 'msg': self._(
                        u'Validation error: There was an error in the XML definition of the '
                        u'examples provided by the user. Please correct the XML definition before saving.')
                    }
                except KeyError:
                    return {'success': False, 'msg': self._(
                        u'Validation error: No examples were provided for example based assessment.'
                    )}
                    # This is where we default to EASE for problems which are edited in the GUI
                assessment['algorithm_id'] = 'ease'

        xblock_validator = validator(self, self._)
        success, msg = xblock_validator(
            create_rubric_dict(data['prompt'], data['criteria']),
            data['assessments'],
            submission_start=data['submission_start'],
            submission_due=data['submission_due'],
            leaderboard_show=data['leaderboard_show']
        )
        if not success:
            return {'success': False, 'msg': self._('Validation error: {error}').format(error=msg)}

        # Calculate track_changes URL
        track_changes_url = ''
        for assessment in data['assessments']:
            track_changes_url = track_changes_url or assessment.get('track_changes', '')

        # At this point, all the input data has been validated,
        # so we can safely modify the XBlock fields.
        self.title = data['title']
        self.display_name = data['title']
        self.prompt = data['prompt']
        self.rubric_criteria = data['criteria']
        self.rubric_assessments = data['assessments']
        self.editor_assessments_order = data['editor_assessments_order']
        self.track_changes = track_changes_url
        self.rubric_feedback_prompt = data['feedback_prompt']
        self.rubric_feedback_default_text = data['feedback_default_text']
        self.submission_start = data['submission_start']
        self.submission_due = data['submission_due']
        self.allow_file_upload = bool(data['allow_file_upload'])
        self.allow_latex = bool(data['allow_latex'])
        self.leaderboard_show = data['leaderboard_show']

        return {'success': True, 'msg': self._(u'Successfully updated OpenAssessment XBlock')}

    @XBlock.json_handler
    def check_released(self, data, suffix=''):
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
            'success': True, 'msg': u'',
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

        student_training_template = {'answer': ""}
        criteria_list = copy.deepcopy(self.rubric_criteria_with_labels)
        for criterion in criteria_list:
            criterion['option_selected'] = ""
        student_training_template['criteria'] = criteria_list

        if student_training_module:
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

        example_based_assessment = self.get_assessment_module('example-based-assessment')

        if example_based_assessment:
            assessments['example_based_assessment'] = {
                'examples': serialize_examples_to_xml_str(example_based_assessment)
            }

        return assessments

    def _editor_assessments_order_context(self):
        """
        Create a list of assessment names in the order
        the user last set in the editor, including
        assessments that are not currently enabled.

        Returns:
            list of assessment names

        """
        order = copy.deepcopy(self.editor_assessments_order)
        used_assessments = [asmnt['name'] for asmnt in self.valid_assessments]
        default_editor_order = copy.deepcopy(DEFAULT_EDITOR_ASSESSMENTS_ORDER)

        # Backwards compatibility:
        # If the problem already contains example-based assessment
        # then allow the editor to display example-based assessments.
        if 'example-based-assessment' in used_assessments:
            default_editor_order.insert(0, 'example-based-assessment')

        # Backwards compatibility:
        # If the editor assessments order doesn't match the problem order,
        # fall back to the problem order.
        # This handles the migration of problems created pre-authoring,
        # which will have the default editor order.
        problem_order_indices = [
            order.index(asmnt_name) for asmnt_name in used_assessments
            if asmnt_name in order
        ]
        if problem_order_indices != sorted(problem_order_indices):
            unused_assessments = list(set(default_editor_order) - set(used_assessments))
            return sorted(unused_assessments) + used_assessments

        # Forwards compatibility:
        # Include any additional assessments that may have been added since the problem was created.
        else:
            return order + list(set(default_editor_order) - set(order))
