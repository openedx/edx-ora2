"""
Helper class for loading generated file from webpack.
"""
import json
import logging

from pkg_resources import resource_string
from django.conf import settings

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def urljoin(*args):
    """
    Joining multiple url continuously. The default behavior from os.path.join
    would completely reset the path if the second path start with '/'.
    """
    begining_slash = '/' if args[0].startswith('/') else ''
    trailing_slash = '/' if args[-1].endswith('/') else ''
    joined_path = '/'.join(map(lambda x: str(x).strip('/'), args))
    return begining_slash + joined_path + trailing_slash


class LoadStatic:
    """
    Helper class for loading generated file from webpack.
    """

    _manifest = {}
    _is_dev_server = False
    _is_loaded = False

    @staticmethod
    def reload_manifest():
        """
        Reload from manifest file
        """
        # comment this out while developing
        if LoadStatic._is_loaded:
            return
        try:
            json_data = resource_string(__name__, 'static/dist/manifest.json').decode("utf8")
            LoadStatic._manifest = json.loads(json_data)
            LoadStatic._is_dev_server = LoadStatic._manifest.get('is_dev_server', False)
            LoadStatic._is_loaded = True
        except OSError:
            logger.error('Cannot find static/dist/manifest.json')

    @staticmethod
    def get_url(key):
        """
        get url from key
        """
        LoadStatic.reload_manifest()
        url = LoadStatic._manifest.get(key, key)
        if LoadStatic.get_is_dev_server():
            return url
        return urljoin(settings.STATIC_URL, 'dist', url)

    @staticmethod
    def get_is_dev_server():
        """
        get is_dev_server
        """
        LoadStatic.reload_manifest()
        return LoadStatic._is_dev_server
