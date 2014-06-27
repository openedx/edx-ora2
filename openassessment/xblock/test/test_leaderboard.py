# -*- coding: utf-8 -*-
"""
Tests for leaderboard handlers in Open Assessment XBlock.
"""
import json
import mock
from .base import XBlockHandlerTestCase, scenario

class TestLeaderboardRender(XBlockHandlerTestCase):

    @scenario('data/leaderboard_unavailable.xml')
    def test_unavailable(self, xblock):
        # Start date is in the future for this scenario
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/leaderboard/oa_leaderboard_waiting.html',
            {}
        )

    @scenario('data/leaderboard_show.xml')
    def test_show(self, xblock):
        # Start date is in the future for this scenario
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/leaderboard/oa_leaderboard_show.html',
            {'topscores': []}, 'done'
        )
        #self.assertEqual(1, 2)

    def _assert_path_and_context(
        self, xblock, expected_path, expected_context,
        workflow_status=None, status_details=None,
        submission_uuid=None
    ):
        """
        Render the leaderboard and verify:
            1) that the correct template and context were used
            2) that the rendering occurred without an error

        Args:
            xblock (OpenAssessmentBlock): The XBlock under test.
            expected_path (str): The expected template path.
            expected_context (dict): The expected template context.

        Kwargs:
            workflow_status (str): If provided, simulate this status from the workflow API.
            workflow_status (str): If provided, simulate these details from the workflow API.
            submission_uuid (str): If provided, simulate this submision UUI for the current workflow.
        """
        if workflow_status is not None:
            # Assume a peer-->self flow by default
            if status_details is None:
                status_details = {
                    'peer': {'complete': workflow_status == 'done'},
                    'self': {'complete': workflow_status in ['waiting', 'done']}
                }
            xblock.get_workflow_info = mock.Mock(return_value={
                'status': workflow_status,
                'status_details': status_details,
                'submission_uuid': submission_uuid
            })

        if workflow_status == 'done':
            path, context = xblock.render_leaderboard_complete(submission_uuid)
        else:
            path, context = xblock.render_leaderboard_incomplete()

        self.assertEqual(path, expected_path)
        self.assertItemsEqual(context, expected_context)

        response = xblock.render_leaderboard(None, None)

        # Verify that we render without error
        resp = self.request(xblock, 'render_leaderboard', json.dumps({}))
        self.assertGreater(len(resp), 0)