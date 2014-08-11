# -*- coding: utf-8 -*-
"""
Tests for leaderboard handlers in Open Assessment XBlock.
"""
import json
import mock
from django.core.cache import cache
from submissions import api as sub_api
from .base import XBlockHandlerTransactionTestCase, scenario
from django.test.utils import override_settings
from moto import mock_s3
import boto
from boto.s3.key import Key
from openassessment.fileupload import api

class TestLeaderboardRender(XBlockHandlerTransactionTestCase):

    @scenario('data/basic_scenario.xml')
    def test_no_leaderboard(self, xblock):
        # Since there's no leaderboard set in the problem XML,
        # it should not be visible
        self._assert_leaderboard_visible(xblock, False)

    @scenario('data/leaderboard_unavailable.xml')
    def test_unavailable(self, xblock):
        # Start date is in the future for this scenario
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/leaderboard/oa_leaderboard_waiting.html',
            {}
        )
        self._assert_leaderboard_visible(xblock, True)

    @scenario('data/leaderboard_show.xml')
    def test_show_no_submissions(self, xblock):
        # No submissions created yet, so the leaderboard shouldn't display any scores
        self._assert_scores(xblock, [])
        self._assert_leaderboard_visible(xblock, True)

    @scenario('data/leaderboard_show.xml')
    def test_show_submissions(self, xblock):

        # Create some submissions (but fewer than the max that can be shown)
        self._create_submissions_and_scores(xblock, [
            ("test answer 1", 1),
            ("test answer 2", 2)
        ])
        self._assert_scores(xblock, [
            {"content": "test answer 2", "score": 2},
            {"content": "test answer 1", "score": 1}
        ])
        self._assert_leaderboard_visible(xblock, True)

        # Since leaderboard results are cached, we need to clear
        # the cache in order to see the new scores.
        cache.clear()

        # Create more submissions than the max
        self._create_submissions_and_scores(xblock, [
            ("test answer 3", 0),
            ("test answer 4", 10),
            ("test answer 5", 3)
        ])
        self._assert_scores(xblock, [
            {"content": "test answer 4", "score": 10},
            {"content": "test answer 5", "score": 3},
            {"content": "test answer 2", "score": 2}
        ])
        self._assert_leaderboard_visible(xblock, True)

    @scenario('data/leaderboard_show.xml')
    def test_no_text_key_submission(self, xblock):
        # Instead of using the default submission as a dict with "text",
        # make the submission a string.
        self._create_submissions_and_scores(xblock, [("test answer", 1)], submission_key=None)

        # It should still work
        self._assert_scores(xblock, [
            {"content": "test answer", "score": 1}
        ])

    @scenario('data/leaderboard_show.xml')
    def test_non_text_submission(self, xblock):
        # Create a non-text submission (the submission dict doesn't contain "text")
        self._create_submissions_and_scores(xblock, [("s3key", 1)], submission_key="file_key")

        # Expect that we default to an empty string for content
        self._assert_scores(xblock, [
            {"content": "", "score": 1, "file": ""}
        ])

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @scenario('data/leaderboard_show_allowfiles.xml')
    def test_image_and_text_submission(self, xblock):
        # Create a file and get the download URL
        conn = boto.connect_s3()
        bucket = conn.create_bucket('mybucket')
        key = Key(bucket)
        key.key = "submissions_attachments/foo"
        key.set_contents_from_string("How d'ya do?")
        downloadUrl = api.get_download_url("foo")
        # Create a image and text submission
        self._create_submissions_and_scores(xblock, [({"text": "test answer", "file_key": "foo"}, 1)], submission_key=None)

        # Expect that we retrieve both the text and the download URL for the file
        self._assert_scores(xblock, [
            {"content": "test answer", "score": 1, "file": downloadUrl}
        ])

    def _create_submissions_and_scores(
        self, xblock, submissions_and_scores,
        submission_key="text", points_possible=10
    ):
        """
        Create submissions and scores that should be displayed by the leaderboard.

        Args:
            xblock (OpenAssessmentBlock)
            submisions_and_scores (list): List of `(submission, score)` tuples, where
                `submission` is the essay text (string) and `score` is the integer
                number of points earned.

        Keyword Args:
            points_possible (int): The total number of points possible for this problem
            submission_key (string): The key to use in the submission dict.  If None, use
                the submission value itself instead of embedding it in a dictionary.
        """
        for num, (submission, points_earned) in enumerate(submissions_and_scores):
            # Assign a unique student ID
            # These aren't displayed by the leaderboard, so we can set them
            # to anything without affecting the test.
            student_item = xblock.get_student_item_dict()
            student_item['student_id'] = "student {num}".format(num=num)

            if submission_key is not None:
                answer = { submission_key: submission }
            else:
                answer = submission

            # Create a submission
            sub = sub_api.create_submission(student_item, answer)

            # Create a score for the submission
            sub_api.set_score(sub['uuid'], points_earned, points_possible)

    def _assert_scores(self, xblock, scores):
        """
        Check that the leaderboard displays the expected scores.

        Args:
            xblock (OpenAssessmentBlock)
            scores (list): The scores displayed by the leaderboard, each of which
                is a dictionary of with keys 'content' (the submission text)
                and 'score' (the integer number of points earned)
        """
        self._assert_path_and_context(
            xblock,
            'openassessmentblock/leaderboard/oa_leaderboard_show.html',
            {
                'topscores': scores
            },
            workflow_status='done'
        )

    def _assert_path_and_context(self, xblock, expected_path, expected_context, workflow_status=None):
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

        Raises:
            AssertionError

        """
        if workflow_status is not None:
            xblock.get_workflow_info = mock.Mock(return_value={ 'status': workflow_status })

        if workflow_status == 'done':
            path, context = xblock.render_leaderboard_complete(xblock.get_student_item_dict())
        else:
            path, context = xblock.render_leaderboard_incomplete()

        self.assertEqual(path, expected_path)
        self.assertEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_leaderboard', json.dumps({}))
        self.assertGreater(len(resp), 0)

    def _assert_leaderboard_visible(self, xblock, is_visible):
        """
        Check that the leaderboard is displayed in the student view.
        """
        fragment = self.runtime.render(xblock, "student_view")
        has_leaderboard = 'openassessment__leaderboard' in fragment.body_html()
        self.assertEqual(has_leaderboard, is_visible)
