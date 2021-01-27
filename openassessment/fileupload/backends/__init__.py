""" File Upload backends. """


from django.conf import settings

from . import django_storage, filesystem, s3, swift


def get_backend():
    # .. setting_name: ORA2_FILEUPLOAD_BACKEND
    # .. setting_default: 's3'
    # .. setting_description: The backend used to upload the ora2 submissions attachments.
    #     The supported values are: 's3', 'filesystem', 'swift' and 'django'.
    backend_setting = getattr(settings, "ORA2_FILEUPLOAD_BACKEND", "s3")
    if backend_setting == "s3":
        return s3.Backend()
    elif backend_setting == "filesystem":
        return filesystem.Backend()
    elif backend_setting == "swift":
        return swift.Backend()
    elif backend_setting == "django":
        return django_storage.Backend()
    else:
        raise ValueError("Invalid ORA2_FILEUPLOAD_BACKEND setting value: %s" % backend_setting)
