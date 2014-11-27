from . import s3
from . import filesystem

from django.conf import settings


def get_backend():
    # Use S3 backend by default (current behaviour)
    backend_setting = getattr(settings, "ORA2_FILEUPLOAD_BACKEND", "s3")
    if backend_setting == "s3":
        return s3.Backend()
    elif backend_setting == "filesystem":
        return filesystem.Backend()
    else:
        raise ValueError("Invalid ORA2_FILEUPLOAD_BACKEND setting value: %s" % backend_setting)
