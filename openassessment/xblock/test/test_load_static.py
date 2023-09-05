"""
Test load static class
"""

from unittest.mock import patch
from django.test import TestCase, override_settings
from openassessment.xblock.load_static import LoadStatic, urljoin


class TestLoadStatic(TestCase):
    """Test load static class"""

    def setUp(self):
        LoadStatic._manifest = {}   # pylint: disable=protected-access
        LoadStatic._is_loaded = False   # pylint: disable=protected-access
        LoadStatic._is_dev_server = False   # pylint: disable=protected-access
        return super().setUp()

    def test_urljoin(self):
        expected_result_1 = 'path_1/path_2'
        expected_result_2 = 'path_1/path_2/'
        expected_result_3 = '/path_1/path_2'
        expected_result_4 = '/path_1/path_2/'

        self.assertEqual(expected_result_1, urljoin('path_1', 'path_2'))
        self.assertEqual(expected_result_1, urljoin('path_1/', 'path_2'))
        self.assertEqual(expected_result_1, urljoin('path_1', '/path_2'))
        self.assertEqual(expected_result_1, urljoin('path_1/', '/path_2'))

        self.assertEqual(expected_result_2, urljoin('path_1', 'path_2/'))
        self.assertEqual(expected_result_2, urljoin('path_1/', 'path_2/'))
        self.assertEqual(expected_result_2, urljoin('path_1', '/path_2/'))
        self.assertEqual(expected_result_2, urljoin('path_1/', '/path_2/'))

        self.assertEqual(expected_result_3, urljoin('/path_1', 'path_2'))
        self.assertEqual(expected_result_3, urljoin('/path_1/', 'path_2'))
        self.assertEqual(expected_result_3, urljoin('/path_1', '/path_2'))
        self.assertEqual(expected_result_3, urljoin('/path_1/', '/path_2'))

        self.assertEqual(expected_result_4, urljoin('/path_1', 'path_2/'))
        self.assertEqual(expected_result_4, urljoin('/path_1/', 'path_2/'))
        self.assertEqual(expected_result_4, urljoin('/path_1', '/path_2/'))
        self.assertEqual(expected_result_4, urljoin('/path_1/', '/path_2/'))

    def test_get_url_default(self):
        key_url = 'some_url.js'
        self.assertEqual(LoadStatic.get_url(key_url), urljoin('/static', 'dist', key_url))

    @override_settings(STATIC_URL='/cms')
    def test_get_url_with_custom_static_url(self):
        key_url = 'some_url.js'
        self.assertEqual(LoadStatic.get_url(key_url), urljoin('/cms', 'dist', key_url))

    @patch('pkg_resources.resource_string')
    def test_is_dev_server_url(self, resource_string):
        resource_string.return_value = None
        key_url = 'some_url.js'
        with patch('json.loads') as jsondata:
            jsondata.return_value = dict({
                'some_url.js': 'some_url.hash.js',
                'is_dev_server': True
            })
            self.assertEqual(LoadStatic.get_is_dev_server(), True)
            self.assertEqual(LoadStatic.get_url(key_url), 'some_url.hash.js')

    @patch('pkg_resources.resource_string')
    def test_get_url_file_not_found(self, resource_string):
        key_url = 'some_url.js'
        resource_string.side_effect = IOError()
        self.assertEqual(LoadStatic.get_url(key_url), urljoin('/static', 'dist', key_url))
