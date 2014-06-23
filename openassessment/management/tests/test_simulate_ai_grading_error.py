# -*- coding: utf-8 -*-
"""
Tests for the simulate AI grading error management command.
"""

from django.test.utils import override_settings
from openassessment.test_utils import CacheResetTest
from openassessment.management.commands import simulate_ai_grading_error
from openassessment.assessment.models import AIGradingWorkflow
from openassessment.assessment.worker.grading import grade_essay


class SimulateAIGradingErrorTest(CacheResetTest):
    """
    Tests for the simulate AI grading error management command.
    """

    COURSE_ID = u"TɘꙅT ↄoUᴙꙅɘ"
    ITEM_ID = u"𝖙𝖊𝖘𝖙 𝖎𝖙𝖊𝖒"
    NUM_SUBMISSIONS = 20

    AI_ALGORITHMS = {
        "fake": "openassessment.assessment.worker.algorithm.FakeAIAlgorithm"
    }

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_simulate_ai_grading_error(self):
        # Run the command
        cmd = simulate_ai_grading_error.Command()
        cmd.handle(
            self.COURSE_ID.encode('utf-8'),
            self.ITEM_ID.encode('utf-8'),
            self.NUM_SUBMISSIONS,
            "fake"
        )

        # Check that the correct number of incomplete workflows
        # were created.  These workflows should still have
        # a classifier set, though, because otherwise they
        # wouldn't have been scheduled for grading
        # (that is, the submissions were made before classifier
        # training completed).
        incomplete_workflows = AIGradingWorkflow.objects.filter(
            classifier_set__isnull=False,
            completed_at__isnull=True
        )
        num_errors = incomplete_workflows.count()
        self.assertEqual(self.NUM_SUBMISSIONS, num_errors)

        # Verify that we can complete the workflows successfully
        # (that is, make sure the classifier data is valid)
        # We're calling a Celery task method here,
        # but we're NOT using `apply_async`, so this will
        # execute synchronously.
        for workflow in incomplete_workflows:
            grade_essay(workflow.uuid)

        # Now there should be no incomplete workflows
        remaining_incomplete = AIGradingWorkflow.objects.filter(
            classifier_set__isnull=False,
            completed_at__isnull=True
        ).count()
        self.assertEqual(remaining_incomplete, 0)
