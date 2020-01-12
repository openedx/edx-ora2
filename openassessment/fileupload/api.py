"""
The File Upload application is designed to allow the management of files
associated with submissions. This can be used to upload new files, manage
URLs of existing files, and delete files.
"""

from __future__ import absolute_import, unicode_literals

import json
import logging
from django.db import IntegrityError

from openassessment.assessment.models import SharedFileUpload
from openassessment.fileupload.exceptions import FileUploadError

from . import backends


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def get_upload_url(key, content_type):
    """
    Returns a url (absolute or relative, depending on the endpoint) which can be used to upload a file to.
    """
    return backends.get_backend().get_upload_url(key, content_type)


def get_download_url(key):
    """
    Returns the url at which the file that corresponds to the key can be downloaded.
    """
    return backends.get_backend().get_download_url(key)


def remove_file(key):
    """
    Remove file from the storage
    """
    return backends.get_backend().remove_file(key)


def get_student_file_key(student_item_dict, index=0):
    """
    Args:
        student_item_dict: A dictionary containing keys ('student_id', 'course_id', 'item_id').
        index (int, optional): The index of a file.
    """
    key_template = '{student_id}/{course_id}/{item_id}'
    index = int(index)
    if index > 0:
        key_template += '/{index}'
    return key_template.format(index=index, **student_item_dict)


def _safe_load_json_list(field, log_error=False):
    """
    Tries to load JSON-ified string,
    returns an empty list if we try to load some non-JSON-encoded string.
    """
    try:
        return json.loads(field)
    except ValueError:
        if log_error:
            logger.exception("URLWorkaround: Safe Load failed for data field:{field} with type:{type}".format(
                field=field,
                type=type(field)
            ))
        return []


class FileUpload(object):
    """
    A layer of abstraction over the various components of file
    data stored as ORA XBlock user-scoped fields.
    """
    def __init__(self, name=None, description=None, size=None, index=None, descriptionless=False, **student_item_dict):
        """
        Args:
            name (str): The name of a file.
            description (str): The student-provided description of a file.
            size (int): The size, in bytes, of a file.
            index (int): The position of a file relative to all other uploaded files for a given user.
            descriptionless (bool): True if this file exists but has no description, name, or size.
                                    False (default) otherwise.
            student_item_dict (dict): Contains the student_id, course_id, and item_id, i.e. the "student item"
                                      triple associated with this file upload.
        """
        self.name = name
        self.description = description
        self.size = size
        self.index = index
        self.student_id = student_item_dict.get('student_id')
        self.course_id = student_item_dict.get('course_id')
        self.item_id = student_item_dict.get('item_id')
        self.descriptionless = descriptionless

    @property
    def exists(self):
        return (self.description is not None) or self.descriptionless

    @property
    def download_url(self):
        if self.exists:
            try:
                return get_download_url(self.key)
            except FileUploadError as exc:
                logger.exception(u'FileUploadError: URL retrieval failed for key {key} with error {error}'.format(
                    key=self.key,
                    error=exc
                ))
                return ''

    @property
    def key(self):
        """
        Simple utility method to generate a common file upload key based on
        the student item.

        Returns:
            A string representation of the key.
        """
        student_item_dict = {
            'student_id': self.student_id,
            'course_id': self.course_id,
            'item_id': self.item_id,
        }
        return get_student_file_key(student_item_dict, index=self.index)

    def url_descriptor_tuple(self):
        """
        Used in the response template context to provide a file URL, description, and name
        to render in the client.
        """
        return (self.download_url, self.description, self.name)

    def _to_dict(self):
        """
        Returns:
            A dictionary representation of the FileUpload.
        """
        attrs = ('description', 'name', 'size', 'course_id', 'student_id', 'item_id', 'descriptionless')
        return {
            key: getattr(self, key, None) for key in attrs
        }

    def __eq__(self, other):
        """
        Returns:
            True if self's dict representation equals other's dict representation,
            False otherwise.
        """
        return self._to_dict() == other._to_dict()  # pylint: disable=protected-access


class FileUploadManager(object):
    """
    Manages the CRUD operations of file uploads
    that take place in the context of an OpenAssessmentBlock.

    e.g. inside an XBlock:
    self.upload_manager = FileUploadManager(self)
    for file_upload in self.upload_manager.get_uploads():
        log.info(file_upload.download_url)

    new_uploads = [
        {'name': 'file-1.jpg', 'description': 'File 1', 'size': 1024},
        {'name': 'file-2.jpg', 'description': 'File 2', 'size': 2048},
    ]
    self.upload_manager.append_uploads(*new_uploads)

    self.upload_manager.delete_upload(index=0)
    """
    def __init__(self, openassessment_xblock):
        self.block = openassessment_xblock

    def get_uploads(self, include_deleted=False):
        """
        Returns:
            A list of FileUpload objects associated with an instance of an O.A. Block.
        """
        descriptions, names, sizes = self._get_metadata_from_block()
        return self._file_uploads_from_list_fields(
            descriptions, names, sizes, include_deleted
        )

    def append_uploads(self, *new_uploads):
        """
        Given lists of new file metadata, write the new metadata to our stored file metadata fields

        Args:
            descriptions_to_add: a list of file descriptions
            names_to_add: a list of file names
            sizes_to_add: a list of file sizes as integers

        Returns: newly updated file metadata fields
        """
        required_keys = ('description', 'name', 'size')
        try:
            (
                descriptions_to_add,
                names_to_add,
                sizes_to_add,
            ) = self._dicts_to_key_lists(new_uploads, required_keys)
        except FileUploadError as exc:
            logging.exception(u"FileUploadError: Metadata save for {data} failed with error {error}".format(
                error=exc,
                data=new_uploads
            ))
            raise

        existing_file_descriptions, existing_file_names, existing_file_sizes = self._get_metadata_from_block()

        new_descriptions = existing_file_descriptions + descriptions_to_add
        self._set_file_descriptions(new_descriptions)

        new_names = existing_file_names + names_to_add
        self._set_file_names(new_names)

        new_sizes = existing_file_sizes + sizes_to_add
        self._set_file_sizes(new_sizes)

        new_file_uploads = self._file_uploads_from_list_fields(new_descriptions, new_names, new_sizes)

        if self.block.is_team_assignment():
            existing_file_upload_key_set = {
                fileupload.key for fileupload in
                self._file_uploads_from_list_fields(
                    existing_file_descriptions,
                    existing_file_names,
                    existing_file_sizes
                )
            }
            for new_file_upload in new_file_uploads:
                if new_file_upload.key not in existing_file_upload_key_set:
                    self.create_shared_upload(new_file_upload)

        return new_file_uploads

    def create_shared_upload(self, fileupload):
        try:
            SharedFileUpload.objects.create(
                team_id=self.block.team.team_id,
                owner_id=fileupload.student_id,
                course_id=fileupload.course_id,
                item_id=fileupload.item_id,
                file_key=fileupload.key,
                description=fileupload.description,
                size=fileupload.size,
                name=fileupload.name,
            )
        except IntegrityError as e:
            logger.error("Unable to create shared upload. " + str(e))
            raise e

    def delete_upload(self, index):
        """
        Given a file index to remove, null out its metadata in our stored file metadata fields

        Args:
            index: file index to remove

        Returns: newly updated FileUpload records.
        """
        file_key = get_student_file_key(self.block.get_student_item_dict(), index)
        remove_file(file_key)

        stored_file_descriptions, stored_file_names, stored_file_sizes = self._get_metadata_from_block()

        stored_file_descriptions[index] = None
        self._set_file_descriptions(stored_file_descriptions)

        stored_file_names[index] = None
        self._set_file_names(stored_file_names)

        stored_file_sizes[index] = 0
        self._set_file_sizes(stored_file_sizes)

    def _get_metadata_from_block(self):
        descriptions = self._get_file_descriptions()
        names = self._get_file_names(descriptions)
        sizes = self._get_file_sizes(descriptions)
        return descriptions, names, sizes

    def _file_uploads_from_list_fields(self, descriptions, names, sizes, include_deleted=False):
        """
        Given file upload data as list fields, return a list of FileUploads constructed from those fields
        """
        file_fields_by_key = {
            'name': names,
            'description': descriptions,
            'size': sizes,
        }

        if not descriptions:
            return self._descriptionless_uploads()

        file_uploads = []
        for index in range(len(descriptions)):
            file_upload_kwargs = {
                key: file_field[index] for key, file_field in file_fields_by_key.items()
            }

            file_upload_kwargs.update(self.block.get_student_item_dict())
            file_upload_kwargs['index'] = index

            file_upload = FileUpload(**file_upload_kwargs)
            if include_deleted or file_upload.exists:
                file_uploads.append(file_upload)

        return file_uploads

    def _descriptionless_uploads(self):
        """
        This is the old behavior, required for a corner case and should be eventually removed.
        https://github.com/edx/edx-ora2/pull/1275 closed a loophole that allowed files
        to be uploaded without descriptions. In that case, an ORA block's saved_file_descriptions would be
        an empty list, but a key corresponding to their student item information would exist (and thus,
        so would a valid download URL).
        If there are users in that state who have files uploaded
        with no descriptions but have not yet submitted, they will fall here.
        """
        file_uploads = []

        student_item_dict = self.block.get_student_item_dict()
        for index in range(self.block.MAX_FILES_COUNT):
            file_key = get_student_file_key(student_item_dict, index)

            download_url = ''
            try:
                download_url = get_download_url(file_key)
            except FileUploadError:
                pass

            if download_url:
                file_uploads.append(FileUpload(
                    name='', description='', size=0, index=index, descriptionless=True, **student_item_dict
                ))
            else:
                break

        return file_uploads

    def _get_file_descriptions(self):
        """ Returns a list of file descriptions associated with this manager's OA block. """
        return _safe_load_json_list(self.block.saved_files_descriptions)

    def _set_file_descriptions(self, file_description_list):
        """ Updates the file descriptions associated with this manager's OA block. """
        self.block.saved_files_descriptions = json.dumps(file_description_list)

    def _get_file_names(self, descriptions=None):
        """ Returns a list of file names associated with this manager's OA block. """
        descriptions = descriptions or self._get_file_descriptions()
        file_names = _safe_load_json_list(self.block.saved_files_names)
        if len(file_names) != len(descriptions):
            file_names = [None for _ in range(len(descriptions))]
            self._set_file_names(file_names)
        return file_names

    def _set_file_names(self, file_name_list):
        """ Updates the list of file names associated with this manager's OA block. """
        self.block.saved_files_names = json.dumps(file_name_list)

    def _get_file_sizes(self, descriptions=None):
        """ Returns a list of file sizes associated with this manager's OA block. """
        descriptions = descriptions or self._get_file_descriptions()
        file_sizes = _safe_load_json_list(self.block.saved_files_sizes)
        if len(file_sizes) != len(descriptions):
            file_sizes = [None for _ in range(len(descriptions))]
            self._set_file_sizes(file_sizes)
        return file_sizes

    def _set_file_sizes(self, file_size_list):
        self.block.saved_files_sizes = json.dumps(file_size_list)

    def _dicts_to_key_lists(self, dicts, required_keys):
        """
        Transposes a list of dictionaries with certain required keys
        to a tuple of lists, each containing the values of the required keys.
        """
        result = {
            key: [] for key in required_keys
        }

        for _dict in dicts:
            for key in required_keys:
                if key not in _dict:
                    raise FileUploadError('Missing required key {} in {}'.format(key, _dict))
                result[key].append(_dict[key])

        return tuple(result[key] for key in required_keys)
