"""
The File Upload application is designed to allow the management of files
associated with submissions. This can be used to upload new files, manage
URLs of existing files, and delete files.
"""

from collections import namedtuple
import json
import logging

from django.db import IntegrityError
from django.utils.functional import cached_property

from openassessment.assessment.models.base import SharedFileUpload
from openassessment.fileupload.exceptions import FileUploadError

from . import backends


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

KEY_SEPARATOR = '/'


def get_upload_url(key, content_type):
    """
    Returns a url (absolute or relative, depending on the endpoint) which can be used to upload a file to.
    """
    return backends.get_backend().get_upload_url(key, content_type)


def get_download_url(key):
    """
    Returns the url at which the file that corresponds to the key can be downloaded.
    """
    url = backends.get_backend().get_download_url(key)
    if not url:
        logger.warning('FileUploadError: Could not retrieve URL for key %s', key)
    return url


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
    key_template = KEY_SEPARATOR.join(('{student_id}', '{course_id}', '{item_id}'))
    index = int(index)
    if index > 0:
        key_template += KEY_SEPARATOR + '{index}'
    return key_template.format(index=index, **student_item_dict)


def can_delete_file(current_user_id, teams_enabled, key, team_id=None, shared_file=None):
    """
    A user is allowed to delete any file they own if this is not a team-enabled response.
    If the response is team-enabled, a user, who is a member of a team,
    is allowed to delete a file they own as long as they are still
    a member of the team with which the file has been shared.

    params:
      current_user_id (string): The anonymous id of the current user in an ORA block.
      teams_enabled (boolean): Indicates if teams are enabled for an ORA block.
      key (string): The key of the file to check if we can delete.
      team_id (string): The id of the team of the user who may be able to delete the file.
      shared_file (SharedFileUpload): Optional. A SharedFileUpload object corresponding to the given
      key.  It's useful to pass this in if you've already fetched all of the SharedFileUpload records
      for a given item/team.

    raises:
        SharedFileUpload.DoesNotExist If teams are enabled, a team_id is provided,
        and no SharedFileUpload corresponding to the file key exists.
    returns:
        Boolean indicating if the file with the given key can be deleted by the current user.
    """
    if not teams_enabled:
        return True

    if not shared_file:
        try:
            shared_file = SharedFileUpload.by_key(key)
        except SharedFileUpload.DoesNotExist:
            logger.info('While checking ORA file-deletion ability, could not find file with key: %s', key)
            return True

    if shared_file.owner_id != current_user_id:
        return False

    if shared_file.team_id != team_id:
        return False

    # If we've made it this far, the current user has a team, and it's the same
    # team that the file is shared with, so let them (as the file's owner) delete it.
    return True


def delete_shared_files_for_team(course_id, item_id, team_id):
    """
    Delete shared files for a team for this block
    """
    uploads = SharedFileUpload.by_team_course_item(team_id, course_id, item_id)

    for upload in uploads:
        remove_file(upload.file_key)
        upload.delete()


def _safe_load_json_list(field, log_error=False):
    """
    Tries to load JSON-ified string,
    returns an empty list if we try to load some non-JSON-encoded string.
    """
    try:
        return json.loads(field)
    except ValueError:
        if log_error:
            logger.exception(
                "URLWorkaround: Safe Load failed for data field:%s with type:%s", field, type(field)
            )
        return []


class FileUpload:
    """
    A layer of abstraction over the various components of file
    data stored as ORA XBlock user-scoped fields.
    """
    def __init__(self, name=None, description=None, size=None, index=0, descriptionless=False, **student_item_dict):
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
        """
        Returns the url at which the file that corresponds to the key
        can be downloaded if exists.
        """
        if self.exists:
            try:
                return get_download_url(self.key)
            except FileUploadError as exc:
                logger.exception(
                    'FileUploadError: URL retrieval failed for key %s with error %s',
                    self.key,
                    exc,
                    exc_info=True,
                )
                return ''
        return None

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

    def __hash__(self):
        """
        Returns a hash of the FileUpload's dict representation
        """
        return hash(self._to_dict())


FileDescriptor = namedtuple('FileDescriptor', ['download_url', 'description', 'name', 'show_delete_button'])
TeamFileDescriptor = namedtuple('TeamFileDescriptor', ['download_url', 'description', 'name', 'uploaded_by'])


class FileUploadManager:
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
        self.shared_uploads_for_team_by_key_cache = dict()

    @cached_property
    def student_item_dict(self):
        """ Returns a dict containing 'student_id', 'course_id', and 'item_id'. """
        return self.block.get_student_item_dict()

    def get_uploads(self, team_id=None, include_deleted=False):
        """
        Returns:
            A list of FileUpload objects associated with an instance of an Open Assessment Block.
            This will include FileUpload objects corresponding to existing files.
            It does **not** include entries for files that have been deleted.
        """
        descriptions, names, sizes = self._get_metadata_from_block()
        user_uploads = self._file_uploads_from_list_fields(descriptions, names, sizes, include_deleted=include_deleted)

        if self.block.is_team_assignment():
            return self._uploads_shared_with_team_by_current_user(user_uploads, team_id)

        return user_uploads

    def get_team_uploads(self, team_id=None):
        if self.block.is_team_assignment():
            return self._uploads_owned_by_teammates(team_id)
        return []

    def _uploads_shared_with_team_by_current_user(self, user_uploads, team_id):
        """
        Helper function that filters a given list of ``user_uploads``
        down to those ``FileUploads`` that are owned by the current user
        **and** the given team
        """
        jointly_owned_uploads = []

        for upload in user_uploads:
            shared_upload = self.shared_uploads_for_student_by_key.get(upload.key)
            if shared_upload and (shared_upload.team_id == team_id):
                jointly_owned_uploads.append(upload)
            elif not upload.exists:
                # we should return entries for deleted files, here,
                # to uphold the invariant around file indices.
                jointly_owned_uploads.append(upload)

        return jointly_owned_uploads

    def _uploads_owned_by_teammates(self, team_id):
        """
        Returns a list of FileUpload objects owned by other members of the given team.
        Does not include FileUploads of the current user.
        """
        shared_uploads_from_other_users = sorted(
            [
                shared_upload
                for shared_upload in self.shared_uploads_for_team_by_key(team_id).values()
                if shared_upload.owner_id != self.student_item_dict['student_id']
            ],
            key=lambda upload: upload.file_key,
        )

        return [
            FileUpload(
                name=shared_upload.name,
                description=shared_upload.description,
                size=shared_upload.size,
                student_id=shared_upload.owner_id,
                course_id=shared_upload.course_id,
                item_id=shared_upload.item_id,
                index=shared_upload.index,
            ) for shared_upload in shared_uploads_from_other_users
        ]

    def file_descriptors(self, team_id=None, include_deleted=False):
        """
        Used in the response template context to provide file information
        (file URL, description, name, show_delete_button) for each uploaded
        file in this block.

        If self.block is team-enabled, this will return only entries for files
        that have been shared with the specified team
        """

        descriptors = []

        for upload in self.get_uploads(team_id=team_id, include_deleted=include_deleted):
            show_delete_button = bool(upload.exists)

            if upload.exists and self.block.is_team_assignment():
                shared_upload = self.shared_uploads_for_team_by_key(team_id)[upload.key]
                show_delete_button = can_delete_file(
                    self.student_item_dict['student_id'],
                    self.block.is_team_assignment(),
                    upload.key,
                    team_id=team_id,
                    shared_file=shared_upload,
                )

            descriptors.append(FileDescriptor(
                download_url=upload.download_url,
                description=upload.description,
                name=upload.name,
                show_delete_button=show_delete_button,
            )._asdict())

        return descriptors

    def team_file_descriptors(self, team_id=None):
        """
        Returns the list of TeamFileDescriptors owned by other team members
        shown to a user when self.block is a team assignment.
        """
        return [
            TeamFileDescriptor(
                download_url=upload.download_url,
                description=upload.description,
                name=upload.name,
                uploaded_by=self.block.get_username(upload.student_id)
            )._asdict()
            for upload in self.get_team_uploads(team_id=team_id)
        ]

    @cached_property
    def shared_uploads_for_student_by_key(self):
        """
        Returns **and caches** all of the SharedFileUpload records
        for this student/course/item.
        """
        shared_uploads = SharedFileUpload.by_student_course_item(**self.student_item_dict)
        return {shared_upload.file_key: shared_upload for shared_upload in shared_uploads}

    def shared_uploads_for_team_by_key(self, team_id):
        """
        Returns **and caches** all of the SharedFileUpload records
        for this student/course/item and team.

        Realistically, only one team_id will ever be requested, but this is a simple enough pattern
        """
        if team_id not in self.shared_uploads_for_team_by_key_cache:
            shared_uploads = SharedFileUpload.by_team_course_item(
                team_id=team_id,
                course_id=self.student_item_dict['course_id'],
                item_id=self.student_item_dict['item_id'],
            )
            shared_uploads_for_team_by_key = {
                shared_upload.file_key: shared_upload for shared_upload in shared_uploads
            }
            self.shared_uploads_for_team_by_key_cache[team_id] = shared_uploads_for_team_by_key
        return self.shared_uploads_for_team_by_key_cache[team_id]

    def invalidate_cached_shared_file_dicts(self):
        """
        Invalidates SharedFileUpload records that we have cached.
        """
        if hasattr(self, 'shared_uploads_for_student_by_key'):
            del self.shared_uploads_for_student_by_key

        self.shared_uploads_for_team_by_key_cache = dict()

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
            logging.exception(
                "FileUploadError: Metadata save for %s failed with error %s",
                exc,
                new_uploads
            )
            raise

        existing_file_descriptions, existing_file_names, existing_file_sizes = self._get_metadata_from_block()

        new_descriptions = existing_file_descriptions + descriptions_to_add
        self._set_file_descriptions(new_descriptions)

        new_names = existing_file_names + names_to_add
        self._set_file_names(new_names)

        new_sizes = existing_file_sizes + sizes_to_add
        self._set_file_sizes(new_sizes)

        new_file_uploads = self._file_uploads_from_list_fields(new_descriptions, new_names, new_sizes)

        if self.block.is_team_assignment() and self.block.has_team():
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

        self.invalidate_cached_shared_file_dicts()
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
            logger.error("Unable to create shared upload. %s", str(e))
            raise e

    def get_file_key(self, index):
        return get_student_file_key(self.student_item_dict, index)

    def delete_upload(self, index):
        """
        Given a file index to remove, null out its metadata in our stored file metadata fields.
        This will also delete any ``SharedFileUpload`` records associated with the file's key
        (if the file has been shared with a team).

        Args:
            index (integer): file index to remove
        """
        file_key = self.get_file_key(index)
        remove_file(file_key)

        stored_file_descriptions, stored_file_names, stored_file_sizes = self._get_metadata_from_block()

        stored_file_descriptions[index] = None
        self._set_file_descriptions(stored_file_descriptions)

        stored_file_names[index] = None
        self._set_file_names(stored_file_names)

        stored_file_sizes[index] = 0
        self._set_file_sizes(stored_file_sizes)

        if self.block.is_team_assignment():
            try:
                SharedFileUpload.by_key(file_key).delete()
            except SharedFileUpload.DoesNotExist:
                logger.warning('Could not find SharedFileUpload to delete: %s', file_key)

        self.invalidate_cached_shared_file_dicts()

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

            file_upload_kwargs.update(self.student_item_dict)
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

        for index in range(self.block.MAX_FILES_COUNT):
            file_key = get_student_file_key(self.student_item_dict, index)

            download_url = ''
            try:
                download_url = get_download_url(file_key)
            except FileUploadError:
                pass

            if download_url:
                file_uploads.append(FileUpload(
                    name='', description='', size=0, index=index, descriptionless=True, **self.student_item_dict
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
