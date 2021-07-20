"""
Helper class for loading generated file from webpack.
"""
import json
import logging

from pkg_resources import resource_string
from django.conf import settings

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class LoadStatic:
    """
    Helper class for loading generated file from webpack.
    """

    _manifest = dict()
    _base_url = ''
    _is_loaded = False

    @staticmethod
    def reload_manifest():
        """
        Reload from manifest file
        """
        try:
            json_data = resource_string(__name__, 'static/dist/manifest.json').decode("utf8")
            LoadStatic._manifest = json.loads(json_data)
            LoadStatic._is_loaded = True
            if LoadStatic._manifest['is_dev_server']:
                LoadStatic._base_url = LoadStatic._manifest['base_url']
            elif hasattr(settings, 'LMS_ROOT_URL'):
                LoadStatic._base_url = settings.LMS_ROOT_URL + LoadStatic._manifest['base_url']
            else:
                LoadStatic._base_url = LoadStatic._manifest['base_url']
                logger.error('LMS_ROOT_URL is undefined')
        except IOError:
            LoadStatic._base_url = '/static/dist/'
            logger.error('Cannot find static/dist/manifest.json')

    @staticmethod
    def get_url(key):
        """
        get url from key
        """
        if not LoadStatic._is_loaded:
            LoadStatic.reload_manifest()
        url = LoadStatic._manifest[key] if LoadStatic._is_loaded else key
        return LoadStatic._base_url + url
