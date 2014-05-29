# -*- coding: utf-8 -*-
"""
Tests for the simulate AI grading error management command.
"""

from openassessment.test_utils import CacheResetTest
from openassessment.management.commands import simulate_ai_grading_error
from openassessment.assessment.models import AIGradingWorkflow


class SimulateAIGradingErrorTest(CacheResetTest):
    """
    Tests for the simulate AI grading error management command.
    """

    COURSE_ID = u"TɘꙅT ↄoUᴙꙅɘ"
    ITEM_ID = u"𝖙𝖊𝖘𝖙 𝖎𝖙𝖊𝖒"
    NUM_SUBMISSIONS = 20


    def test_simulate_ai_grading_error(self):
        # Run the command
        cmd = simulate_ai_grading_error.Command()
        cmd.handle(
            self.COURSE_ID.encode('utf-8'),
            self.ITEM_ID.encode('utf-8'),
            self.NUM_SUBMISSIONS
        )

        # Check that the correct number of incomplete workflows
        # were created.  These workflows should still have
        # a classifier set, though, because otherwise they
        # wouldn't have been scheduled for grading
        # (that is, the submissions were made before classifier
        # training completed).
        num_errors = AIGradingWorkflow.objects.filter(
            classifier_set__isnull=False,
            completed_at__isnull=True
        ).count()
        self.assertEqual(self.NUM_SUBMISSIONS, num_errors)
