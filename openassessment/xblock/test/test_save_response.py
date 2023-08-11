"""
Test that the student can save a response.
"""
import json
from unittest import mock

import ddt

from openassessment.xblock.data_conversion import prepare_submission_for_serialization

from .base import XBlockHandlerTestCase, scenario


@ddt.ddt
class SaveResponseTest(XBlockHandlerTestCase):
    """ Test Responses are saved correctly. """

    @scenario('data/save_scenario.xml', user_id="Daniels")
    def test_default_saved_response_blank(self, xblock):
        xblock.get_team_info = mock.Mock(return_value={})

        xblock.is_due_date_extension_enabled = mock.Mock(return_value=True)

        xblock.xmodule_runtime = mock.Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id='test_course',
            anonymous_student_id='Pmn'
        )

        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn('Response not started.', resp.decode('utf-8'))

    @ddt.file_data('data/save_responses.json')
    @scenario('data/save_scenario.xml', user_id="Perleman")
    def test_save_response(self, xblock, data):
        xblock.get_team_info = mock.Mock(return_value={})

        xblock.is_due_date_extension_enabled = mock.Mock(return_value=True)

        xblock.xmodule_runtime = mock.Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id='test_course',
            anonymous_student_id='Pmn'
        )

        # Save the response
        submission = ["  ".join(data[0]), "  ".join(data[1])]
        payload = json.dumps({'submission': submission})
        resp = self.request(xblock, 'save_submission', payload, response_format="json")
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], '')

        # Reload the submission UI
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn(submission[0], resp.decode('utf-8'))
        self.assertIn(submission[1], resp.decode('utf-8'))
        self.assertIn('draft saved!', resp.decode('utf-8').lower())

    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_overwrite_saved_response(self, xblock):
        xblock.get_team_info = mock.Mock(return_value={})

        # XBlock has a saved response already
        xblock.saved_response = prepare_submission_for_serialization([
            "THAT'ꙅ likɘ A 40-bɘgᴙɘɘ bAY.",
            "Aiᴎ'T ᴎodobY goT ᴎoTHiᴎg To ꙅAY AdoUT A 40-bɘgᴙɘɘ bAY."
        ])

        # Save another response
        submission = ["ГЂіи lіиэ ъэтшээи", "Ђэаvэи аиↁ Ђэѓэ."]
        payload = json.dumps({'submission': submission})
        resp = self.request(xblock, 'save_submission', payload, response_format="json")
        self.assertTrue(resp['success'])

        # Verify that the saved response was overwritten
        self.assertEqual(xblock.saved_response, json.dumps(prepare_submission_for_serialization(submission)))

    @scenario('data/save_scenario.xml', user_id="Bubbles")
    def test_missing_submission_key(self, xblock):
        xblock.get_team_info = mock.Mock(return_value={})

        resp = self.request(xblock, 'save_submission', json.dumps({}), response_format="json")
        self.assertFalse(resp['success'])
        self.assertIn('Submission data missing. Please contact support staff.', resp['msg'])
