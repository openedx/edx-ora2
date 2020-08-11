"""
Tests for other functions related to the management of file uploads, without testing
anything related to backends.
"""
import json

import mock
import pytest

from openassessment.assessment.models.base import SharedFileUpload
from openassessment.fileupload import api


DEFAULT_COURSE_ID = 'a-fun-course'
DEFAULT_ITEM_ID = 'a-fun-item'
DEFAULT_TEAM_ID = 'the-a-team'
DEFAULT_OWNER_ID = 'my-owner-id'


# pylint: disable=redefined-outer-name
@pytest.fixture
def shared_file_upload_fixture():
    """
    Helper method to create a SharedFileUpload object and
    delete it on exit.
    """
    DEFAULT_SHARED_FILE_KWARGS = {
        'file_key': 'my-key',
        'team_id': DEFAULT_TEAM_ID,
        'course_id': DEFAULT_COURSE_ID,
        'item_id': DEFAULT_ITEM_ID,
        'owner_id': DEFAULT_OWNER_ID,
    }

    created_uploads = []

    def _make_shared_file_upload(**kwargs):
        """ Inner function that creates ``SharedFileUpload`` objects. """
        upload_kwargs = {key: value for key, value in DEFAULT_SHARED_FILE_KWARGS.items()}
        upload_kwargs.update(kwargs)
        upload = SharedFileUpload.objects.create(**upload_kwargs)
        created_uploads.append(upload)
        return upload

    yield _make_shared_file_upload

    for upload in created_uploads:
        upload.delete()


@pytest.fixture
def mock_block():
    """ Test fixture that returns a stand-in for an ORA XBlock. """
    mock_block = mock.Mock()
    mock_block.get_student_item_dict.return_value = {
        'student_id': DEFAULT_OWNER_ID,
        'course_id': DEFAULT_COURSE_ID,
        'item_id': DEFAULT_ITEM_ID,
    }

    mock_block.get_username = mock.Mock(
        return_value='some_username'
    )

    def _make_mock_block(**kwargs):
        mock_block.saved_files_descriptions = json.dumps(kwargs.get('descriptions') or ['file-description-1'])
        mock_block.saved_files_names = json.dumps(kwargs.get('names') or ['file-name-1.pdf'])
        mock_block.saved_files_sizes = json.dumps(kwargs.get('sizes') or [77])
        return mock_block

    yield _make_mock_block


@pytest.mark.django_db
def test_can_delete_file_if_teams_not_enabled():
    assert api.can_delete_file(DEFAULT_OWNER_ID, False, 'any-key', DEFAULT_TEAM_ID) is True


@pytest.mark.django_db
def test_can_delete_file_if_file_not_shared_and_not_on_team():
    assert api.can_delete_file(DEFAULT_OWNER_ID, True, 'a-different-key', None) is True


@pytest.mark.django_db
def test_cannot_delete_file_if_file_shared_and_not_on_team(shared_file_upload_fixture):
    _ = shared_file_upload_fixture()
    assert api.can_delete_file(DEFAULT_OWNER_ID, True, 'my-key', None) is False


@pytest.mark.django_db
def test_can_delete_file_if_key_not_found_in_shared_files():
    assert api.can_delete_file(DEFAULT_OWNER_ID, True, 'any-key', DEFAULT_TEAM_ID) is True


@pytest.mark.django_db
def test_can_delete_file_if_team_ids_match(shared_file_upload_fixture):
    assert api.can_delete_file(
        DEFAULT_OWNER_ID,
        True,
        'my-key',
        DEFAULT_TEAM_ID,
        shared_file=shared_file_upload_fixture(),
    ) is True


@pytest.mark.django_db
def test_can_delete_file_if_team_ids_match_shared_file_excluded(shared_file_upload_fixture):
    _ = shared_file_upload_fixture()

    assert api.can_delete_file(
        DEFAULT_OWNER_ID,
        True,
        'my-key',
        DEFAULT_TEAM_ID,
    ) is True


@pytest.mark.django_db
def test_cannot_delete_file_if_team_ids_do_not_match(shared_file_upload_fixture):
    assert api.can_delete_file(
        DEFAULT_OWNER_ID,
        True,
        'my-key',
        'a-different-team-id',
        shared_file=shared_file_upload_fixture(),
    ) is False


@pytest.mark.django_db
def test_cannot_delete_file_if_user_ids_do_not_match(shared_file_upload_fixture):
    assert api.can_delete_file(
        'a-different-student-id',
        True,
        'my-key',
        DEFAULT_TEAM_ID,
        shared_file=shared_file_upload_fixture(),
    ) is False


@pytest.mark.django_db
@mock.patch('openassessment.fileupload.api.remove_file', autospec=True)
def test_delete_shared_files_for_team(mock_remove_file, shared_file_upload_fixture, mock_block):
    # Given some shared files for a team, among other similar files
    files_to_delete = [{'file_key': 'key-1'}, {'file_key': 'key-2'}, {'file_key': 'key-3'}]
    same_team_different_block = [{'file_key': 'key-4', 'item_id': 'not the item you\'re looking for'}]
    different_team_same_block = [{'file_key': 'key-5', 'team_id': 'team_rocket'}]

    all_files = files_to_delete + same_team_different_block + different_team_same_block

    for file_info in all_files:
        _ = shared_file_upload_fixture(**file_info)

    assert SharedFileUpload.objects.all().count() == len(all_files)

    # When I ask to delete the files
    api.delete_shared_files_for_team(DEFAULT_COURSE_ID, DEFAULT_ITEM_ID, DEFAULT_TEAM_ID)

    # Each file is removed from the backend and the models are deleted
    assert mock_remove_file.call_count == len(files_to_delete)
    assert SharedFileUpload.objects.all().count() == len(all_files) - len(files_to_delete)


@pytest.mark.django_db
def test_shared_uploads_for_student_by_key(shared_file_upload_fixture, mock_block):
    file_keys = ['key-1', 'key-2', 'key-3']

    for file_key in file_keys:
        _ = shared_file_upload_fixture(file_key=file_key)

    block = mock_block()
    file_manager = api.FileUploadManager(block)

    shared_uploads_by_key = file_manager.shared_uploads_for_student_by_key

    assert len(shared_uploads_by_key) == 3

    for expected_key in file_keys:
        shared_file_upload = shared_uploads_by_key[expected_key]

        assert shared_file_upload.team_id == DEFAULT_TEAM_ID
        assert shared_file_upload.course_id == DEFAULT_COURSE_ID
        assert shared_file_upload.item_id == DEFAULT_ITEM_ID


@pytest.mark.django_db
def test_file_descriptor_tuples_no_team(mock_block):
    block = mock_block(
        descriptions=['The first file', 'The second file'],
        names=['File A', 'File B'],
        sizes=[22, 44],
    )
    block.is_team_assignment.return_value = False

    file_manager = api.FileUploadManager(block)

    actual_descriptors = file_manager.file_descriptor_tuples()
    expected_descriptors = [
        api.FileDescriptor(download_url='', name='File A', description='The first file', show_delete_button=True),
        api.FileDescriptor(download_url='', name='File B', description='The second file', show_delete_button=True),
    ]

    assert expected_descriptors == actual_descriptors


@pytest.mark.django_db
@mock.patch('openassessment.fileupload.api.remove_file', autospec=True)
@mock.patch('openassessment.fileupload.api.get_download_url', autospec=True)
def test_file_descriptor_tuples_after_sharing_with_old_team(
        mock_get_download_url, mock_remove_file, shared_file_upload_fixture, mock_block
):
    # Include a deleted file entry, and later assert that we have an empty FileDescriptor
    # record returned by ``file_descriptor_tuples()``
    block = mock_block(
        descriptions=['The first file', 'The deleted file', 'The second file'],
        names=['File A', 'File that is deleted', 'File B'],
        sizes=[22, 666, 44],
    )
    block.team.team_id = DEFAULT_TEAM_ID
    block.is_team_assignment.return_value = True

    student_item_dict = {
        'student_id': DEFAULT_OWNER_ID,
        'course_id': DEFAULT_COURSE_ID,
        'item_id': DEFAULT_ITEM_ID,
    }
    key_a = api.get_student_file_key(student_item_dict, index=0)
    key_deleted = api.get_student_file_key(student_item_dict, index=1)
    key_b = api.get_student_file_key(student_item_dict, index=2)

    # create a shared upload that was shared with an old team
    _ = shared_file_upload_fixture(team_id='an-old-team', file_key=key_a)

    # create one for the file we're going to delete
    _ = shared_file_upload_fixture(team_id=block.team.team_id, file_key=key_deleted)

    # create a shared upload that's shared with the learner's current team
    _ = shared_file_upload_fixture(team_id=block.team.team_id, file_key=key_b)

    file_manager = api.FileUploadManager(block)

    # go and delete the file we want to delete
    file_manager.delete_upload(1)

    # team_file_descriptor_tuples() should only give back a record for the upload shared with the current team
    actual_descriptors = file_manager.file_descriptor_tuples(include_deleted=True)
    expected_descriptors = [
        api.FileDescriptor(
            download_url=None,
            name=None,
            description=None,
            show_delete_button=False,
        ),
        api.FileDescriptor(
            download_url=mock_get_download_url.return_value,
            name='File B',
            description='The second file',
            show_delete_button=True,
        ),
    ]

    assert expected_descriptors == actual_descriptors
    mock_get_download_url.assert_called_once_with(key_b)
    mock_remove_file.assert_called_once_with(key_deleted)


@pytest.mark.django_db
@mock.patch('openassessment.fileupload.api.get_download_url', autospec=True)
def test_team_file_descriptor_tuples(mock_get_download_url, shared_file_upload_fixture, mock_block):
    mock_get_download_url.return_value = "some-download-url"
    block = mock_block(
        descriptions=['The first file'],
        names=['File A'],
        sizes=[22],
    )
    block.team.team_id = DEFAULT_TEAM_ID
    block.is_team_assignment.return_value = True

    student_item_dict = {
        'student_id': DEFAULT_OWNER_ID,
        'course_id': DEFAULT_COURSE_ID,
        'item_id': DEFAULT_ITEM_ID,
    }
    key_a = api.get_student_file_key(student_item_dict, index=0)

    # create a shared upload that's shared with the learner's current team
    _ = shared_file_upload_fixture(team_id=block.team.team_id, file_key=key_a)

    # create a couple of files uploaded by teammates
    key_beta = api.get_student_file_key(
        {'student_id': 'another-student', 'course_id': DEFAULT_COURSE_ID, 'item_id': DEFAULT_ITEM_ID}
    )
    _ = shared_file_upload_fixture(
        description='Another file',
        name='File Beta',
        team_id=block.team.team_id,
        owner_id='another-student',
        file_key=key_beta,
    )

    key_delta = api.get_student_file_key(
        {'student_id': 'yet-another-student', 'course_id': DEFAULT_COURSE_ID, 'item_id': DEFAULT_ITEM_ID}
    )
    _ = shared_file_upload_fixture(
        description='Yet another file',
        name='File Delta',
        team_id=block.team.team_id,
        owner_id='yet-another-student',
        file_key=key_delta,
    )

    file_manager = api.FileUploadManager(block)

    # team_file_descriptor_tuples() should only give back records for files owned by teammates
    actual_descriptors = file_manager.team_file_descriptor_tuples()

    expected_descriptors = [
        api.TeamFileDescriptor(
            download_url=mock_get_download_url.return_value,
            name='File Beta',
            description='Another file',
            uploaded_by='some_username',
        ),
        api.TeamFileDescriptor(
            download_url=mock_get_download_url.return_value,
            name='File Delta',
            description='Yet another file',
            uploaded_by='some_username',
        ),
    ]
    assert expected_descriptors == actual_descriptors
    mock_get_download_url.assert_has_calls([
        mock.call(key_beta),
        mock.call(key_delta),
    ])
