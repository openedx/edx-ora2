""" Filesystem backend for file upload. """


from pathlib import Path

from django.conf import settings
import django.core.cache
from django.urls import reverse
from django.utils.encoding import smart_text

from .. import exceptions
from .base import BaseBackend


class Backend(BaseBackend):
    """
    Upload openassessment student files to a local filesystem. Note
    that in order to use this file storage backend, you need to include the
    urls from openassessment.fileupload in your urls.py file:

    E.g:
        url(r'^openassessment/storage', include(openassessment.fileupload.urls)),

    The ORA2_FILEUPLOAD_CACHE_NAME setting will also have to be defined for the
    name of the django.core.cache instance which will maintain the list of
    active storage URLs.

    E.g:

        ORA2_FILEUPLOAD_CACHE_NAME = "ora2-storage"
        CACHES = {
            ...
            'ora2-storage': {
                'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                ...
            },
            ...
        }
    """

    def get_upload_url(self, key, content_type):
        make_upload_url_available(self._get_key_name(key), self.UPLOAD_URL_TIMEOUT)
        return self._get_url(key)

    def get_download_url(self, key):
        key_name = self._get_key_name(key)
        if self._file_exists(key_name):
            make_download_url_available(key_name, self.DOWNLOAD_URL_TIMEOUT)
            return self._get_url(key)
        return None

    def remove_file(self, key):
        from openassessment.fileupload.views_filesystem import safe_remove, get_file_path
        return safe_remove(get_file_path(self._get_key_name(key)))

    def _get_url(self, key):
        key_name = self._get_key_name(key)
        url = reverse("openassessment-filesystem-storage", kwargs={'key': key_name})
        return url

    def _file_exists(self, key_name):
        from openassessment.fileupload.views_filesystem import get_file_path

        file_path = get_file_path(key_name)
        file_path = Path(file_path)
        return file_path.exists()


def get_cache():
    """
    Returns a django.core.cache instance in charge of maintaining the
    authorized upload and download URL.

    Raises:
        FileUploadInternalError if the cache name setting is not defined.
        InvalidCacheBackendError if the corresponding cache backend has not
        been configured.
    """
    cache_name = getattr(settings, "ORA2_FILEUPLOAD_CACHE_NAME", None)
    if cache_name is None:
        raise exceptions.FileUploadInternalError("Undefined cache backend for file upload")
    return django.core.cache.caches[cache_name]


def make_upload_url_available(url_key_name, timeout):
    """
    Authorize an upload URL.

    Arguments:
        url_key_name (str): key that uniquely identifies the upload url
        timeout (int): time in seconds before the url expires
    """
    get_cache().set(
        smart_text(get_upload_cache_key(url_key_name)),
        1, timeout
    )


def make_download_url_available(url_key_name, timeout):
    """
    Authorize a download URL.

    Arguments:
        url_key_name (str): key that uniquely identifies the url
        timeout (int): time in seconds before the url expires
    """
    get_cache().set(
        smart_text(get_download_cache_key(url_key_name)),
        1, timeout
    )


def is_upload_url_available(url_key_name):
    """
    Return True if the corresponding upload URL is available.
    """
    return get_cache().get(smart_text(get_upload_cache_key(url_key_name))) is not None


def is_download_url_available(url_key_name):
    """
    Return True if the corresponding download URL is available.
    """
    return get_cache().get(smart_text(get_download_cache_key(url_key_name))) is not None


def get_upload_cache_key(url_key_name):
    if isinstance(url_key_name, bytes):
        url_key_name = url_key_name.decode('utf-8')
    return "upload/" + url_key_name


def get_download_cache_key(url_key_name):
    if isinstance(url_key_name, bytes):
        url_key_name = url_key_name.decode('utf-8')
    return "download/" + url_key_name
