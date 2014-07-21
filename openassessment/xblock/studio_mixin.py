"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import copy
import logging
from uuid import uuid4
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _
from dateutil.parser import parse as parse_date
import pytz
from voluptuous import MultipleInvalid
from xblock.core import XBlock
from xblock.fragment import Fragment
from openassessment.xblock import xml
from openassessment.xblock.validation import validator
from openassessment.xblock.data_conversion import create_rubric_dict
from openassessment.xblock.schema import EDITOR_UPDATE_SCHEMA
from openassessment.xblock.resolve_dates import resolve_dates


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
        Retrieve the XBlock's content definition.

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
            [(asmnt.get('start'), asmnt.get('due')) for asmnt in self.valid_assessments]
        )

        submission_start, submission_due = date_ranges[0]
        assessments = self._assessments_editor_context(date_ranges[1:])

        used_assessments, unused_assessments = self._get_assessment_order_and_use()

        # Every rubric requires one criterion. If there is no criteria
        # configured for the XBlock, return one empty default criterion, with
        # an empty default option.
        criteria = copy.deepcopy(self.rubric_criteria_with_labels)
        if not criteria:
            criteria = self.DEFAULT_CRITERIA

        return {
            'prompt': self.prompt,
            'title': self.title,
            'submission_due': submission_due,
            'submission_start': submission_start,
            'assessments': assessments,
            'criteria': criteria,
            'feedbackprompt': self.rubric_feedback_prompt,
            'unused_assessments': unused_assessments,
            'used_assessments': used_assessments,
            'allow_file_upload': self.allow_file_upload
        }

    @XBlock.json_handler
    def update_editor_context(self, data, suffix=''):
        """
        Update the XBlock's configuration.

        Args:
            data (dict): Data from the request; should have a value for the keys: 'rubric', 'prompt',
            'title', 'submission_start', 'submission_due', and 'assessments'.
                -- The 'rubric' should be an XML representation of the new rubric.
                -- The 'prompt' and 'title' should be plain text.
                -- The dates 'submission_start' and 'submission_due' are both ISO strings
                -- The 'assessments' is a list of assessment dictionaries (much like self.rubric_assessments)
                   with the notable exception that all examples (for Student Training and eventually AI)
                   are in XML string format and need to be parsed into dictionaries.

        Kwargs:
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
            return {'success': False, 'msg': _('Error updating XBlock configuration')}

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

        xblock_validator = validator(self)
        success, msg = xblock_validator(
            create_rubric_dict(data['prompt'], data['criteria']),
            data['assessments'],
            submission_start=data['submission_start'],
            submission_due=data['submission_due'],
        )
        if not success:
            return {'success': False, 'msg': _('Validation error: {error}').format(error=msg)}

        # At this point, all the input data has been validated,
        # so we can safely modify the XBlock fields.
        self.title = data['title']
        self.prompt = data['prompt']
        self.rubric_criteria = data['criteria']
        self.rubric_assessments = data['assessments']
        self.rubric_feedback_prompt = data['feedback_prompt']
        self.submission_start = data['submission_start']
        self.submission_due = data['submission_due']
        self.allow_file_upload = bool(data['allow_file_upload'])

        return {'success': True, 'msg': _(u'Successfully updated OpenAssessment XBlock')}

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
            name = asmnt['name']
            template_name = name.replace('-', '_')
            assessments[template_name] = copy.deepcopy(asmnt)
            assessments[template_name]['start'] = date_range[0]
            assessments[template_name]['due'] = date_range[1]

        # In addition to the data in the student training assessment, we need to include two additional
        # pieces of information: a blank context to render the empty template with, and the criteria
        # for each example (so we don't have any complicated logic within the template). Though this
        # could be accomplished within the template, we are opting to remove logic from the template.
        student_training_module = self.get_assessment_module('student-training')

        student_training_template = {'answer': ""}
        criteria_list = copy.deepcopy(self.rubric_criteria)
        for criterion in criteria_list:
            criterion['option_selected'] = ""
        student_training_template['criteria'] = criteria_list

        if student_training_module:
            example_list = []
            # Adds each example to a modified version of the student training module dictionary.
            for example in student_training_module['examples']:
                criteria_list = copy.deepcopy(self.rubric_criteria)
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

    def _get_assessment_order_and_use(self):
        """
        Returns the names of assessments that should be displayed to the author, in the format that
        our template expects, and in the order in which they are currently stored in the OA problem
        definition.

        Returns:
            Tuple of the form ((list of str), (list of str))
                Between the two lists, all of the assessment modules that the author should see are displayed.
        """
        used_assessments = []

        for assessment in self.rubric_assessments:
            used_assessments.append(
                assessment['name'].replace('-','_')
            )

        # NOTE: This is a perfect opportunity to gate the author to allow or disallow Example Based Assessment.
        all_assessments = {'student_training', 'peer_assessment', 'self_assessment', 'example_based_assessment'}
        unused_assessments = list(all_assessments - set(used_assessments))

        return used_assessments, unused_assessments
