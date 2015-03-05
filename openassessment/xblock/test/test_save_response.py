# -*- coding: utf-8 -*-
"""
Test that the student can save a response.
"""
import json
import ddt

from openassessment.xblock.data_conversion import prepare_submission_for_serialization
from .base import XBlockHandlerTestCase, scenario


@ddt.ddt
class SaveResponseTest(XBlockHandlerTestCase):

    @scenario('data/save_scenario.xml', user_id="Daniels")
    def test_default_saved_response_blank(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn('response has not been saved', resp)

    @ddt.file_data('data/save_responses.json')
    @scenario('data/save_scenario.xml', user_id="Perleman")
    def test_save_response(self, xblock, data):
        # Save the response
        submission = ["  ".join(data[0]), "  ".join(data[1])]
        payload = json.dumps({'submission': submission })
        resp = self.request(xblock, 'save_submission', payload, response_format="json")
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], u'')

        # Reload the submission UI
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn(submission[0], resp.decode('utf-8'))
        self.assertIn(submission[1], resp.decode('utf-8'))
        self.assertIn('saved but not submitted', resp.lower())

    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_overwrite_saved_response(self, xblock):

        # XBlock has a saved response already
        xblock.saved_response = prepare_submission_for_serialization([
            u"THAT'ꙅ likɘ A 40-bɘgᴙɘɘ bAY.",
            u"Aiᴎ'T ᴎodobY goT ᴎoTHiᴎg To ꙅAY AdoUT A 40-bɘgᴙɘɘ bAY."
        ])

        # Save another response
        submission = [u"ГЂіи lіиэ ъэтшээи", u"Ђэаvэи аиↁ Ђэѓэ."]
        payload = json.dumps({'submission': submission })
        resp = self.request(xblock, 'save_submission', payload, response_format="json")
        self.assertTrue(resp['success'])

        # Verify that the saved response was overwritten
        self.assertEqual(xblock.saved_response, json.dumps(prepare_submission_for_serialization(submission)))

    @scenario('data/save_scenario.xml', user_id="Bubbles")
    def test_missing_submission_key(self, xblock):
        resp = self.request(xblock, 'save_submission', json.dumps({}), response_format="json")
        self.assertFalse(resp['success'])
        self.assertIn('not submitted', resp['msg'])
