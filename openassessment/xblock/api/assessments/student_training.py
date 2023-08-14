from openassessment.assessment.api import self as self_api
from submissions import api as submission_api

from ..data_conversion import (
    create_submission_dict
)
from ..resolve_dates import DISTANT_FUTURE
from .problem_closed import ProblemClosedAPI
from .workflow import WorkflowAPI

class StudentTrainingAPI:
    def __init__(self, block):
        self.block = block;
        self._is_closed = ProblemClosedAPI(block.is_closed(step="self-assessment"))
        self._workflow = WorkflowAPI(block);

    @property
    def problem_closed(self):
        return self._is_closed.problem_closed

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def start_date(self):
        return self._is_closed.start_date

    @property
    def is_due(self):
        return self._is_closed.is_due

    @property
    def is_past_due(self):
        return self._is_closed.is_past_due

    @property
    def is_not_available_yet(self):
        return self._is_closed.is_not_available_yet

    def _parse_answer_dict(self, answer):
        parts = answer.get('parts', [])
        if parts and isinstance(parts[0], dict) and isinstance(parts[0].get('text'), str):
            return create_submission_dict({'answer': answer}, self.block.prompts)

    def _parse_answer_list(self, answer):
        if answer and isinstance(answer[0], str):
            return self._parse_snwer_string(answer[0])
        elif not answer:
            return self._parse_answer_string('')
        return None

    def _parse_answer_string(self, answer):
        return create_submission_dict({'answer': {'parts': [{'text': answer}]}, self.prompts)

    def _parse_example(self, example):
        if not example:
            return null
        answer = example['answer']
        submission_dict = None
        if isinstance(answer, str):
            submission_dict = self._parse_answer_string(answer)
        elif isinstance(answer, dict):
            submission_dict = self._parse_answer_dict(answer)
        elif isinstance(answer, list):
            submission_dict = self._parse_answer_list(answer)
        return submission_dict

    @property
    def training_module(self):
        return self.block.get_assessment_module('student_training')

    @property
    def num_available(self):
        return len(self.training_module['examples'])

    @property
    def num_completed(self):
        return self.student_training.get_num_completed(self.block.submission_uuid)

    @property
    def examples(self):
        return convert_training_examples_list_to_dict(self.training_module['examples'])
        
    @property
    def example(self):
        return self.student_training.get_training_example(
            self.block.submission_uuid,
            {'prompt': self.prompt, 'criteria': self.block.rubric_criteria_with_labels},
            self.examples
        )

    @property
    def example_context(self):
        context, error_message = self._parse_example(self.example)
        return {
            'error_message': error_message,
            'essay_context': context
        }

    @property
    def example_rubric(self):
        rubric = self.example['rubric']
        return {'criteria': rubric['criteria'], 'points_possible': rubric['points_possible']}
