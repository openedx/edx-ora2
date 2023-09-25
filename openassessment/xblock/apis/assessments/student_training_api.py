"""
External API for ORA Student Training data
"""
from openassessment.assessment.api.student_training import (
    get_num_completed,
    get_training_example,
)

from openassessment.xblock.utils.data_conversion import (
    convert_training_examples_list_to_dict,
    create_submission_dict,
)
from openassessment.xblock.apis.step_data_api import StepDataAPI


class StudentTrainingAPI(StepDataAPI):
    def __init__(self, block):
        super().__init__(block, "student-training")

    def __repr__(self):
        if self.training_module:
            return "{0}".format(
                {
                    "due_date": self.due_date,
                    "has_workflow": self.has_workflow,
                    "is_cancelled": self.is_cancelled,
                    "is_complete": self.is_complete,
                    "is_due": self.is_due,
                    "is_not_available_yet": self.is_not_available_yet,
                    "is_past_due": self.is_past_due,
                    "num_available": self.num_available,
                    "num_completed": self.num_completed,
                    "start_date": self.start_date,
                    "training_module": self.training_module,
                }
            )
        return "{0}".format(
            {
                "due_date": self.due_date,
                "has_workflow": self.has_workflow,
                "is_cancelled": self.is_cancelled,
                "is_complete": self.is_complete,
                "is_due": self.is_due,
                "is_not_available_yet": self.is_not_available_yet,
                "is_past_due": self.is_past_due,
                "start_date": self.start_date,
                "training_module": self.training_module,
            }
        )

    @property
    def example(self):
        return get_training_example(
            self._block.submission_uuid,
            {
                "prompt": self.config_data.prompt,
                "criteria": self._block.rubric_criteria_with_labels,
            },
            self.examples,
        )

    @property
    def example_context(self):
        context, error_message = self._parse_example(self.example)
        return {"error_message": error_message, "essay_context": context}

    @property
    def example_rubric(self):
        rubric = self.example["rubric"]
        return {
            "criteria": rubric["criteria"],
            "points_possible": rubric["points_possible"],
        }

    @property
    def examples(self):
        return convert_training_examples_list_to_dict(self.training_module["examples"])

    @property
    def has_workflow(self):
        return self.workflow_data.has_status

    @property
    def is_cancelled(self):
        return self.workflow_data.is_cancelled

    @property
    def is_complete(self):
        state = self.workflow_data
        return state.has_status and not (state.is_cancelled or state.is_training)

    @property
    def num_available(self):
        return len(self.training_module["examples"])

    @property
    def num_completed(self):
        return get_num_completed(self._block.submission_uuid)

    @property
    def training_module(self):
        return self.config_data.get_assessment_module("student-training")

    def _parse_answer_dict(self, answer):
        """
        Helper to parse answer as a fully-qualified dict.
        """
        parts = answer.get("parts", [])
        if parts and isinstance(parts[0], dict):
            if isinstance(parts[0].get("text"), str):
                return create_submission_dict({"answer": answer}, self.config_data.prompts)
        return None

    def _parse_answer_list(self, answer):
        """
        Helper to parse answer as a list of strings.
        """
        if answer and isinstance(answer[0], str):
            return self._parse_answer_string(answer[0])
        elif not answer:
            return self._parse_answer_string("")
        return None

    def _parse_answer_string(self, answer):
        """
        Helper to parse answer as a plain string
        """
        return create_submission_dict({"answer": {"parts": [{"text": answer}]}}, self.config_data.prompts)

    def _parse_example(self, example):
        """
        EDUCATOR-1263: examples are serialized in a myriad of different ways, we need to be robust to all of them.

        Types of serialized example['answer'] we handle here:
        -fully specified: {'answer': {'parts': [{'text': <response_string>}]}}
        -list of string: {'answer': [<response_string>]}
        -just a string: {'answer': <response_string>}
        """
        if not example:
            return (
                {},
                "No training example was returned fromt he API for student with Submission UUID {}".format(
                    self._block.submission_uuid
                ),
            )
        answer = example["answer"]
        submission_dict = None
        if isinstance(answer, str):
            submission_dict = self._parse_answer_string(answer)
        elif isinstance(answer, dict):
            submission_dict = self._parse_answer_dict(answer)
        elif isinstance(answer, list):
            submission_dict = self._parse_answer_list(answer)
        return (submission_dict, "") or (
            {},
            f"Improperly formatted example, cannot render student training.  Example: {example}",
        )
