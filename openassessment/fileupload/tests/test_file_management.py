import json
import mock

from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from moto import mock_s3

from openassessment.assessment.models.base import SharedFileUpload
from openassessment.fileupload.api import get_student_file_key, FileUpload, FileUploadManager


class MockBlock(object):

    STUDENT_ID = 'student-id-'
    COURSE_ID = 'course-v1:edx+ORA203+course-'
    ITEM_ID = 'itemitemitemitemitem'

    def __init__(self, number, team_id=None, descriptions=None, sizes=None, names=None, max_items=25):
        self.student_id = MockBlock.STUDENT_ID + str(number)
        self.course_id = MockBlock.COURSE_ID + str(number)
        self.item_id = MockBlock.ITEM_ID + str(number)

        empty_list = '[]'
        self.saved_files_descriptions = json.dumps(descriptions) if descriptions else empty_list
        self.saved_files_names = json.dumps(names) if names else empty_list
        self.saved_files_sizes = json.dumps(sizes) if sizes else empty_list
        self.MAX_FILES_COUNT = max_items
        if team_id:
            self.team = mock.MagicMock(
                team_id=team_id,
                course_id=self.COURSE_ID
            )
        else:
            self.team = None

    def has_team(self):
        return bool(self.team)

    def is_team_assignment(self):
        return bool(self.team)

    def get_anonymous_user_id_from_xmodule_runtime(self):
        return self.student_id

    def get_xblock_id(self):
        return self.item_id

    def get_student_item_dict(self):
        return dict(
            student_id=self.student_id,
            item_id=self.item_id,
            course_id=self.course_id,
            item_type='openassessment'
        )


def upload_dict(name, desc, size):
    return {
        'name': name,
        'description': desc,
        'size': size,
    }


class FileUploadManagerTests(TestCase):

    def setUp(self):
        super(FileUploadManagerTests, self).setUp()
        block = MockBlock(1)
        self.manager = FileUploadManager(block)
        self.team_id = 'team_0_id'
        team_block = MockBlock(2, team_id=self.team_id)
        self.team_manager = FileUploadManager(team_block)

    def assert_file_upload(self, file_upload, expected_name, expected_desc, expected_size):
        self.assertEqual(file_upload.name, expected_name)
        self.assertEqual(file_upload.description, expected_desc)
        self.assertEqual(file_upload.size, expected_size)

    @override_settings(ORA2_FILEUPLOAD_BACKEND='django')
    def test_get_append_delete(self):
        files = self.manager.get_uploads()
        self.assertEqual(files, [])

        self.manager.append_uploads(
            upload_dict('name1', 'desc1', 100),
            upload_dict('name2', 'desc2', 200),
            upload_dict('name3', 'desc3', 300),
        )
        files = self.manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assert_file_upload(files[0], 'name1', 'desc1', 100)
        self.assert_file_upload(files[1], 'name2', 'desc2', 200)
        self.assert_file_upload(files[2], 'name3', 'desc3', 300)

        self.manager.append_uploads(
            upload_dict('name4', 'desc4', 400)
        )
        files = self.manager.get_uploads()
        self.assertEqual(4, len(files))
        self.assert_file_upload(files[3], 'name4', 'desc4', 400)

        self.manager.delete_upload(2)
        files = self.manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assert_file_upload(files[0], 'name1', 'desc1', 100)
        self.assert_file_upload(files[1], 'name2', 'desc2', 200)
        self.assert_file_upload(files[2], 'name4', 'desc4', 400)

        self.assertEqual([], self._get_shared_uploads(self.manager))

    def _get_shared_uploads(self, manager):
        return list(SharedFileUpload.objects.filter(
            team_id=self.team_id,
            course_id=manager.block.course_id,
        ).all())

    @override_settings(ORA2_FILEUPLOAD_BACKEND='django')
    def test_shared(self):
        files = self.team_manager.get_uploads()
        self.assertEqual(files, [])
        self.assertEqual(self._get_shared_uploads(self.team_manager), [])

        self.team_manager.append_uploads(
            upload_dict('name1', 'desc1', 100),
            upload_dict('name2', 'desc2', 200),
            upload_dict('name3', 'desc3', 300),
        )
        files = self.team_manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assert_file_upload(files[0], 'name1', 'desc1', 100)
        self.assert_file_upload(files[1], 'name2', 'desc2', 200)
        self.assert_file_upload(files[2], 'name3', 'desc3', 300)
        shared_uploads = self._get_shared_uploads(self.team_manager)
        self.assertEqual(3, len(shared_uploads))
        self.assert_file_upload(shared_uploads[0], 'name1', 'desc1', 100)
        self.assert_file_upload(shared_uploads[1], 'name2', 'desc2', 200)
        self.assert_file_upload(shared_uploads[2], 'name3', 'desc3', 300)
        for shared_upload in shared_uploads:
            self.assertEquals(shared_upload.owner_id, self.team_manager.block.student_id)

        self.team_manager.append_uploads(
            upload_dict('name4', 'desc4', 400)
        )
        files = self.team_manager.get_uploads()
        self.assertEqual(4, len(files))
        self.assert_file_upload(files[3], 'name4', 'desc4', 400)
        shared_uploads = self._get_shared_uploads(self.team_manager)
        self.assert_file_upload(shared_uploads[3], 'name4', 'desc4', 400)
        self.assertEqual(4, len(shared_uploads))
        for shared_upload in shared_uploads:
            self.assertEquals(shared_upload.owner_id, self.team_manager.block.student_id)

        self.team_manager.delete_upload(2)
        files = self.team_manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assert_file_upload(files[0], 'name1', 'desc1', 100)
        self.assert_file_upload(files[1], 'name2', 'desc2', 200)
        self.assert_file_upload(files[2], 'name4', 'desc4', 400)
        shared_uploads = self._get_shared_uploads(self.team_manager)
        self.assertEqual(3, len(shared_uploads))

        shared_upload_names = sorted([upload.name for upload in shared_uploads])
        self.assertEqual(['name1', 'name2', 'name4'], shared_upload_names)

    @override_settings(
        ORA2_FILEUPLOAD_BACKEND='django',
        MEDIA_ROOT='/tmp',
    )
    def test_shared_file_descriptors_have_download_urls(self):
        self.team_manager.append_uploads(
            upload_dict('name1', 'desc1', 100),
            upload_dict('name2', 'desc2', 200),
        )

        # create a new block with a different student_id but on the same team
        other_users_block = MockBlock(number=2, team_id=self.team_id)
        other_users_block.student_id = MockBlock.STUDENT_ID + '317'

        with mock.patch('openassessment.fileupload.backends.django_storage.default_storage') as mock_default_storage:
            mock_default_storage.exists.return_value = True
            other_users_file_manager = FileUploadManager(other_users_block)

            actual_descriptors = other_users_file_manager.team_file_descriptor_tuples()
            self.assertEqual(2, len(actual_descriptors))
            for descriptor in actual_descriptors:
                self.assertEqual(mock_default_storage.url.return_value, descriptor.download_url)

            actual_file_uploads = other_users_file_manager.get_team_uploads()
            self.assertEqual(2, len(actual_file_uploads))
            for index, upload in enumerate(actual_file_uploads):
                self.assertEqual(index, upload.index)

    def test_integrity_error(self):
        self.team_manager.append_uploads(
            upload_dict('name1', 'desc1', 100),
        )
        uploaded_file = self.team_manager.get_uploads()[0]

        with self.assertRaises(IntegrityError):
            self.team_manager.create_shared_upload(uploaded_file)
