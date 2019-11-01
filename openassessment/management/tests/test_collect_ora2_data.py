# -*- coding: utf-8 -*-
""" Test the collect_ora2_data management command """

from __future__ import absolute_import

from mock import patch

from django.core.management import call_command

from openassessment.test_utils import CacheResetTest


class CollectOra2DataTest(CacheResetTest):
    """ Test collect_ora2_data output and error conditions """

    COURSE_ID = u"TɘꙅT ↄoUᴙꙅɘ"

    def setUp(self):
        super(CollectOra2DataTest, self).setUp()

        self.test_header = [
            "submission_uuid",
            "item_id",
            "anonymized_student_id",
            "submitted_at",
            "raw_answer",
            "assessments",
            "assessments_parts",
            "final_score_given_at",
            "final_score_points_earned",
            "final_score_points_possible",
            "feedback_options",
            "feedback",
        ]

        self.test_rows = [
            [
                "33a639de-4e61-11e4-82ab-hash_value",
                "i4x://edX/DemoX/openassessment/hash_value",
                "e31b4beb3d191cd47b07e17735728d53",
                "2014-10-07 20:33:31+00:00",
                u'{""text"": ""This is a response to a question. #dylan""}',
                "Assessment #1 -- scored_at: 2014-10-07 20:37:54 -- type: T -- scorer_id: hash -- feedback: Test",
                "Assessment #1 -- Content: Unclear recommendation (5)",
                "2014-10-07 21:35:47+00:00",
                "10",
                "20",
                "Completed test assessments.",
                u"They were useful.",
            ],
            [
                "row-two-submission-value",
                "i4x://edX/DemoX/openassessment/hash_value",
                "e31b4beb3d191cd47b07e17735728d53",
                "2014-10-07 20:33:31+00:00",
                u'{""text"": ""This is a response to a question. #dylan""}',
                "Assessment #1 -- scored_at: 2014-10-07 20:37:54 -- type: T -- scorer_id: hash -- feedback: Test",
                "Assessment #1 -- Content: Unclear recommendation (5)",
                "2014-10-07 21:35:47+00:00",
                "10",
                "20",
                "Completed test assessments.",
                u"𝓨𝓸𝓾",
            ]
        ]

        self.unicode_encoded_row = [
            "row-two-submission-value",
            "i4x://edX/DemoX/openassessment/hash_value",
            "e31b4beb3d191cd47b07e17735728d53",
            "2014-10-07 20:33:31+00:00",
            u'{""text"": ""This is a response to a question. #dylan""}',
            "Assessment #1 -- scored_at: 2014-10-07 20:37:54 -- type: T -- scorer_id: hash -- feedback: Test",
            "Assessment #1 -- Content: Unclear recommendation (5)",
            "2014-10-07 21:35:47+00:00",
            "10",
            "20",
            "Completed test assessments.",
            "𝓨𝓸𝓾",
        ]

    @patch('openassessment.management.commands.collect_ora2_data.OraAggregateData.collect_ora2_data')
    def test_valid_data_output_to_file(self, mock_data):
        """ Verify that management command writes valid ORA2 data to file. """

        mock_data.return_value = (self.test_header, self.test_rows)

        with patch('openassessment.management.commands.collect_ora2_data.csv') as mock_write:
            call_command('collect_ora2_data', self.COURSE_ID)

            mock_writerow = mock_write.writer.return_value.writerow
            mock_writerow.assert_any_call(self.test_header)
            mock_writerow.assert_any_call(self.test_rows[0])
            mock_writerow.assert_any_call(self.unicode_encoded_row)
