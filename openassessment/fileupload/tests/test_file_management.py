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


def uploadDict(name, desc, size):
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

    def assertFileUpload(self, fileUpload, expectedName, expectedDesc, expectedSize):
        self.assertEqual(fileUpload.name, expectedName)
        self.assertEqual(fileUpload.description, expectedDesc)
        self.assertEqual(fileUpload.size, expectedSize)

    @override_settings(ORA2_FILEUPLOAD_BACKEND='django')
    def test_get_append_delete(self):
        files = self.manager.get_uploads()
        self.assertEqual(files, [])

        self.manager.append_uploads(
            uploadDict('name1', 'desc1', 100),
            uploadDict('name2', 'desc2', 200),
            uploadDict('name3', 'desc3', 300),
        )
        files = self.manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assertFileUpload(files[0], 'name1', 'desc1', 100)
        self.assertFileUpload(files[1], 'name2', 'desc2', 200)
        self.assertFileUpload(files[2], 'name3', 'desc3', 300)

        self.manager.append_uploads(
            uploadDict('name4', 'desc4', 400)
        )
        files = self.manager.get_uploads()
        self.assertEqual(4, len(files))
        self.assertFileUpload(files[3], 'name4', 'desc4', 400)

        self.manager.delete_upload(2)
        files = self.manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assertFileUpload(files[0], 'name1', 'desc1', 100)
        self.assertFileUpload(files[1], 'name2', 'desc2', 200)
        self.assertFileUpload(files[2], 'name4', 'desc4', 400)

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
            uploadDict('name1', 'desc1', 100),
            uploadDict('name2', 'desc2', 200),
            uploadDict('name3', 'desc3', 300),
        )
        files = self.team_manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assertFileUpload(files[0], 'name1', 'desc1', 100)
        self.assertFileUpload(files[1], 'name2', 'desc2', 200)
        self.assertFileUpload(files[2], 'name3', 'desc3', 300)
        shared_uploads = self._get_shared_uploads(self.team_manager)
        self.assertEqual(3, len(shared_uploads))
        self.assertFileUpload(shared_uploads[0], 'name1', 'desc1', 100)
        self.assertFileUpload(shared_uploads[1], 'name2', 'desc2', 200)
        self.assertFileUpload(shared_uploads[2], 'name3', 'desc3', 300)
        for shared_upload in shared_uploads:
            self.assertEquals(shared_upload.owner_id, self.team_manager.block.student_id)

        self.team_manager.append_uploads(
            uploadDict('name4', 'desc4', 400)
        )
        files = self.team_manager.get_uploads()
        self.assertEqual(4, len(files))
        self.assertFileUpload(files[3], 'name4', 'desc4', 400)
        shared_uploads = self._get_shared_uploads(self.team_manager)
        self.assertFileUpload(shared_uploads[3], 'name4', 'desc4', 400)
        self.assertEqual(4, len(shared_uploads))
        for shared_upload in shared_uploads:
            self.assertEquals(shared_upload.owner_id, self.team_manager.block.student_id)

        self.team_manager.delete_upload(2)
        files = self.team_manager.get_uploads()
        self.assertEqual(3, len(files))
        self.assertFileUpload(files[0], 'name1', 'desc1', 100)
        self.assertFileUpload(files[1], 'name2', 'desc2', 200)
        self.assertFileUpload(files[2], 'name4', 'desc4', 400)
        shared_uploads = self._get_shared_uploads(self.team_manager)
        self.assertEqual(4, len(shared_uploads))

    def test_integrity_error(self):
        self.team_manager.append_uploads(
            uploadDict('name1', 'desc1', 100),
        )
        uploaded_file = self.team_manager.get_uploads()[0]

        with self.assertRaises(IntegrityError):
            self.team_manager.create_shared_upload(uploaded_file)
