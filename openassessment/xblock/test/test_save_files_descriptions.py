# -*- coding: utf-8 -*-
"""
Test that the student can save a files descriptions.
"""
import json
import mock

from .base import XBlockHandlerTestCase, scenario


class SaveFilesDescriptionsTest(XBlockHandlerTestCase):
    """
    Group of tests to check ability to save files descriptions

    """

    @scenario('data/save_scenario.xml', user_id="Daniels")
    def test_save_files_descriptions_blank(self, xblock):
        """
        Checks ability to call handler without descriptions.

        """
        resp = self.request(xblock, 'save_files_descriptions', json.dumps({}))
        self.assertIn('descriptions were not submitted', resp)

    @scenario('data/save_scenario.xml', user_id="Perleman")
    def test_save_files_descriptions(self, xblock):
        """
        Checks ability to call handler with descriptions and then saved texts should be available after xblock render.

        """
        # Save the response
        descriptions = [u"Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!", u"Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!"]
        payload = json.dumps({'descriptions': descriptions})
        resp = self.request(xblock, 'save_files_descriptions', payload, response_format="json")
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], u'')

        # Reload the submission UI
        xblock._get_download_url = mock.MagicMock(side_effect=lambda i: "https://img-url/%d" % i)
        resp = self.request(xblock, 'render_submission', json.dumps({}))
        self.assertIn(descriptions[0], resp.decode('utf-8'))
        self.assertIn(descriptions[1], resp.decode('utf-8'))

    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_overwrite_files_descriptions(self, xblock):
        """
        Checks ability to overwrite existed files descriptions.

        """
        descriptions1 = [u"Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!", u"Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!"]
        payload = json.dumps({'descriptions': descriptions1})
        self.request(xblock, 'save_files_descriptions', payload, response_format="json")
        descriptions2 = [u"test1", u"test2"]
        payload = json.dumps({'descriptions': descriptions2})
        self.request(xblock, 'save_files_descriptions', payload, response_format="json")

        # Reload the submission UI
        xblock._get_download_url = mock.MagicMock(side_effect=lambda i: "https://img-url/%d" % i)
        resp = self.request(xblock, 'render_submission', json.dumps({}))

        self.assertNotIn(descriptions1[0], resp.decode('utf-8'))
        self.assertNotIn(descriptions1[1], resp.decode('utf-8'))
        self.assertIn(descriptions2[0], resp.decode('utf-8'))
        self.assertIn(descriptions2[1], resp.decode('utf-8'))
