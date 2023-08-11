"""
Test that the student can save a files descriptions.
"""


import json

from unittest import mock

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
        self.assertIn('descriptions were not submitted', resp.decode('utf-8'))

    @scenario('data/save_scenario.xml', user_id="Perleman")
    def test_save_files_descriptions(self, xblock):
        """
        Checks ability to call handler with descriptions and then saved texts should be available after xblock render.

        """
        # We're not worried about looking up shared uploads in this test
        xblock.has_team = mock.Mock(return_value=False)

        xblock.is_due_date_extension_enabled = mock.Mock(return_value=True)

        xblock.xmodule_runtime = mock.Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id='test_course',
            anonymous_student_id='Pmn'
        )

        # Save the response
        descriptions = [{'description': "Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!", 'fileName': 'fname1', 'fileSize': 1000},
                        {'description': "Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!", 'fileName': 'fname2', 'fileSize': 2000}]
        payload = json.dumps({'fileMetadata': descriptions})
        resp = self.request(xblock, 'save_files_descriptions', payload, response_format="json")
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], '')

        # Reload the submission UI
        # pylint: disable=protected-access,unnecessary-lambda
        with mock.patch('openassessment.fileupload.api.get_download_url') as mock_download_url:
            mock_download_url.side_effect = lambda i: f"https://img-url/{i}"
            resp = self.request(xblock, 'render_submission', json.dumps({}))

        self.assertIn(descriptions[0]['description'], resp.decode('utf-8'))
        self.assertIn(descriptions[1]['description'], resp.decode('utf-8'))

    @scenario('data/save_scenario.xml', user_id="Valchek")
    def test_append_files_descriptions(self, xblock):
        """
        Checks ability to to append additional files

        """
        # We're not worried about looking up shared uploads in this test
        xblock.has_team = mock.Mock(return_value=False)

        xblock.is_due_date_extension_enabled = mock.Mock(return_value=True)

        xblock.xmodule_runtime = mock.Mock(
            user_is_staff=False,
            user_is_beta_tester=False,
            course_id='test_course',
            anonymous_student_id='Pmn'
        )

        descriptions1 = [
            {'description': "Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!", 'fileName': 'fname1', 'fileSize': 1000},
            {'description': "Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!", 'fileName': 'fname2', 'fileSize': 2000}
        ]
        payload = json.dumps({'fileMetadata': descriptions1})
        self.request(xblock, 'save_files_descriptions', payload, response_format="json")
        descriptions2 = [{'description': "test1", 'fileName': 'fname1', 'fileSize': 1000},
                         {'description': "test2", 'fileName': 'fname2', 'fileSize': 2000}]
        payload = json.dumps({'fileMetadata': descriptions2})
        self.request(xblock, 'save_files_descriptions', payload, response_format="json")

        # Reload the submission UI
        # pylint: disable=protected-access,unnecessary-lambda
        with mock.patch('openassessment.fileupload.api.get_download_url') as mock_download_url:
            mock_download_url.side_effect = lambda i: f"https://img-url/{i}"
            resp = self.request(xblock, 'render_submission', json.dumps({}))

        self.assertIn(descriptions1[0]['description'], resp.decode('utf-8'))
        self.assertIn(descriptions1[1]['description'], resp.decode('utf-8'))
        self.assertIn(descriptions2[0]['description'], resp.decode('utf-8'))
        self.assertIn(descriptions2[1]['description'], resp.decode('utf-8'))

    @scenario('data/save_scenario.xml', user_id="Daniels")
    def test_save_files_descriptions_metadata_not_list(self, xblock):
        """
        Should return a failure response when 'fileMetadata' is not a list.
        """
        resp = self.request(xblock, 'save_files_descriptions', json.dumps({'fileMetadata': 1}))
        resp_data = json.loads(resp.decode('utf-8'))

        self.assertFalse(resp_data['success'])
        self.assertIn('descriptions were not submitted', resp_data['msg'])

    @scenario('data/save_scenario.xml', user_id="Daniels")
    def test_save_files_descriptions_metadata_wrong_types(self, xblock):
        """
        Should return a failure response when datatypes in 'fileMetadata'
        are incorrect.
        """
        base_metadata = {
            'description': "Ѕраѓтаиѕ! ГоиіБЂт, Щэ ↁіиэ іи Нэll!",
            'fileName': 'fname1',
            'fileSize': 1000,
        }

        wrong_field_types = {
            'description': 1,
            'fileName': [2, 3, 4],
            'fileSize': '1000',
        }

        for field, wrong_value in wrong_field_types.items():
            file_metadata = dict(base_metadata.items())
            file_metadata[field] = wrong_value

            resp = self.request(xblock, 'save_files_descriptions', json.dumps({'fileMetadata': file_metadata}))
            resp_data = json.loads(resp.decode('utf-8'))

            self.assertFalse(resp_data['success'])
            self.assertIn('descriptions were not submitted', resp_data['msg'])
