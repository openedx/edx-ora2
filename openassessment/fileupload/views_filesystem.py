""" Views for filesystem backend. """


import hashlib
import json
import os

from django.conf import settings
from django.shortcuts import Http404, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import exceptions
from .backends.base import Settings
from .backends.filesystem import is_download_url_available, is_upload_url_available


@require_http_methods(["PUT", "GET"])
def filesystem_storage(request, key):
    """
    Uploading and download files to the local filesystem backend.
    """
    if request.method == "PUT":
        if not is_upload_url_available(key):
            raise Http404()
        content, metadata = get_content_metadata(request)
        save_to_file(key, content, metadata)
        return HttpResponse()
    elif request.method == "GET":
        if not is_download_url_available(key):
            raise Http404()
        return download_file(key)
    return None


def download_file(key):
    """Returns an HttpResponse to download the corresponding file"""

    file_path = get_file_path(key)
    metadata_path = get_metadata_path(key)
    if not os.path.exists(file_path):
        raise Http404()
    with open(metadata_path) as f:
        metadata = json.load(f)
        content_type = metadata.get("Content-Type", 'application/octet-stream')
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=content_type)

    file_name = os.path.basename(os.path.dirname(file_path))
    file_extension = Settings.guess_extension(content_type)
    if not file_name.endswith(file_extension):
        file_name += file_extension
    response['Content-Disposition'] = 'attachment; filename=' + file_name
    return response


def get_content_metadata(request):
    """
    Read the content and metadata associated to an HttpRequest.

    Returns:
        request body (str)
        request metadata (dict)
    """

    metadata = {
        "Content-Type": request.META["CONTENT_TYPE"],
        "Date": str(timezone.now()),
        "Content-MD5": hashlib.md5(request.body).hexdigest(),
        "Content-Length": request.META["CONTENT_LENGTH"],
    }
    return request.body, metadata


def save_to_file(key, content, metadata=None):
    """
    Save the content and metadata to a local file determined by the given key.

    Arguments:
        key (str): unique file identifier
        content (str): uploaded file content
        metadata (dict): json-dumpable data
    """
    file_path = get_file_path(key)
    metadata_path = get_metadata_path(key)
    if metadata is None:
        metadata = {}

    safe_save(file_path, content)
    try:
        safe_save(metadata_path, json.dumps(metadata))
    except Exception:
        safe_remove(file_path)
        safe_remove(metadata_path)
        raise


def safe_save(path, content):
    """
    Save content to path. Creates the appropriate directories, if required.

    Raises:
        FileUploadInternalError if the root directory does not exist or if we
        try to save in an unauthorized directory.
    """
    dir_path = os.path.abspath(os.path.dirname(path))
    if not dir_path.startswith(get_bucket_path()):
        raise exceptions.FileUploadRequestError("Uploaded file name not allowed: '%s'" % path)
    root_directory = get_root_directory_path()
    if not os.path.exists(root_directory):
        raise exceptions.FileUploadInternalError("File upload root directory does not exist: %s" % root_directory)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    mode = "w"
    if isinstance(content, bytes):
        mode = "wb"
    with open(path, mode) as f:
        f.write(content)


def safe_remove(path):
    """Remove a file if it exists.

    Note that an exception will be raised if the file is not writable.
    """
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def get_file_path(key):
    """
    Returns the path to the content file.
    """
    return os.path.join(get_data_path(key), "content")


def get_metadata_path(key):
    """
    Returns the path to the metadata file.
    """
    return os.path.join(get_data_path(key), "metadata.json")


def get_data_path(key):
    """
    Returns the path to the directory which will store the content and metadata
    files.
    """
    subdirectory = key.replace("..", "").strip("/ ")
    return os.path.join(get_bucket_path(), subdirectory)


def get_bucket_path():
    """
    Returns the path to the bucket directory.
    """
    dir_path = os.path.join(
        get_root_directory_path(),
        Settings.get_bucket_name(),
    )
    return os.path.abspath(dir_path)


def get_root_directory_path():
    """
    Returns the path to the root directory in which bucket directories are stored.

    Raises:
        FileUploadInternalError if the root directory setting does not exist.
    """
    root_dir = getattr(settings, "ORA2_FILEUPLOAD_ROOT", None)
    if not root_dir:
        raise exceptions.FileUploadInternalError("Undefined file upload root directory setting")
    return root_dir
