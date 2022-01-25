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
    _base_url = ''
    _is_loaded = False

    @staticmethod
    def reload_manifest():
        """
        Reload from manifest file
        """
        root_url, base_url = '', '/static/dist/'
        if hasattr(settings, 'LMS_ROOT_URL'):
            root_url = settings.LMS_ROOT_URL
        else:
            logger.error('LMS_ROOT_URL is undefined')

        try:
            json_data = resource_string(__name__, 'static/dist/manifest.json').decode("utf8")
            LoadStatic._manifest = json.loads(json_data)
            LoadStatic._is_loaded = True
        except OSError:
            logger.error('Cannot find static/dist/manifest.json')
        finally:
            LoadStatic._base_url = urljoin(root_url, base_url)

    @staticmethod
    def get_url(key):
        """
        get url from key
        """
        if not LoadStatic._is_loaded:
            LoadStatic.reload_manifest()
        url = LoadStatic._manifest[key] if key in LoadStatic._manifest else key
        return urljoin(LoadStatic._base_url, url)
