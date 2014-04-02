# -*- coding: utf-8 -*-
"""
Test that the student can save a response.
"""
import json
import ddt
from .base import XBlockHandlerTestCase, scenario


@ddt.ddt
class SaveResponseTest(XBlockHandlerTestCase):

    @scenario('data/save_scenario.xml', user_id="Daniels")
    def test_default_saved_response_blank(self, xblock):
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn('<textarea id="submission__answer__value" placeholder=""></textarea>', resp)
        self.assertIn('response has not been saved', resp)

    @ddt.file_data('data/save_responses.json')
    @scenario('data/save_scenario.xml', user_id="Perleman")
    def test_save_response(self, xblock, data):
        # Save the response
        submission_text = "  ".join(data)
        payload = json.dumps({'submission': submission_text })
        resp = self.request(xblock, 'save_submission', payload, response_format="json")
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], u'')

        # Reload the submission UI
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        expected_html = u'<textarea id="submission__answer__value" placeholder="">{submitted}</textarea>'.format(
            submitted=submission_text
        )
        self.assertIn(expected_html, resp.decode('utf-8'))
        self.assertIn('saved but not submitted', resp.lower())

    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_overwrite_saved_response(self, xblock):

        # XBlock has a saved response already
        xblock.saved_response = (
            u"THAT'ꙅ likɘ A 40-bɘgᴙɘɘ bAY."
            u"Aiᴎ'T ᴎodobY goT ᴎoTHiᴎg To ꙅAY AdoUT A 40-bɘgᴙɘɘ bAY."
            u"ꟻiꟻTY. dᴙiᴎg A ꙅmilɘ To YoUᴙ ꟻAↄɘ."
        )

        # Save another response
        submission_text = u"ГЂіи lіиэ ъэтшээи Ђэаvэи аиↁ Ђэѓэ."
        payload = json.dumps({'submission': submission_text })
        resp = self.request(xblock, 'save_submission', payload, response_format="json")
        self.assertTrue(resp['success'])

        # Verify that the saved response was overwritten
        self.assertEqual(xblock.saved_response, submission_text)

    @scenario('data/save_scenario.xml', user_id="Bubbles")
    def test_missing_submission_key(self, xblock):
        resp = self.request(xblock, 'save_submission', json.dumps({}), response_format="json")
        self.assertFalse(resp['success'])
        self.assertIn('not submitted', resp['msg'])
