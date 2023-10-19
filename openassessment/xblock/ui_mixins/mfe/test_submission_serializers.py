"""Tests for submission-based serializers"""
from unittest import TestCase
import ddt

from openassessment.fileupload.api import FileDescriptor, TeamFileDescriptor
from openassessment.xblock.ui_mixins.mfe.submission_serializers import (
    DraftResponseSerializer,
    SubmissionSerializer
)
from openassessment.data import OraSubmissionAnswer, SubmissionFileUpload


# pylint: disable=abstract-method,super-init-not-called,arguments-differ
class MockOraSubmissionAnswer(OraSubmissionAnswer):
    def __init__(self, text_responses, file_uploads):
        self.text_responses = text_responses
        self.file_uploads = file_uploads

    def get_text_responses(self):
        return self.text_responses

    def get_file_uploads(self, generate_urls=False):
        return self.file_uploads


def _mock_uploaded_file(file_id):
    return SubmissionFileUpload(
        file_id,
        f'name-{file_id}',
        f'desc-{file_id}',
        size=file_id,
        url=f'www.mysite.com/files/{file_id}'
    )


class TestSubmissionSerializer(TestCase):
    def test_serializer(self):
        mock_text_responses = ["response to prompt 1", "response to prompt 2"]
        mock_uploaded_files = [
            _mock_uploaded_file(file_id) for file_id in [1, 22]
        ]
        data = {
            'workflow': {
                'has_submitted': True,
                'has_cancelled': False,
                'has_received_grade': True,
            },
            'team_info': {
                'team_name': 'Team1',
                'team_usernames': ['Bob', 'Alice'],
                'previous_team_name': None,
                'has_submitted': True,
            },
            'response': MockOraSubmissionAnswer(mock_text_responses, mock_uploaded_files),
            'file_data': []
        }
        assert SubmissionSerializer(data).data == {
            'textResponses': mock_text_responses,
            'uploadedFiles': [
                {
                    'fileUrl': 'www.mysite.com/files/1',
                    'fileDescription': 'desc-1',
                    'fileName': 'name-1',
                    'fileSize': 1,
                    'fileIndex': 0
                },
                {
                    'fileUrl': 'www.mysite.com/files/22',
                    'fileDescription': 'desc-22',
                    'fileName': 'name-22',
                    'fileSize': 22,
                    'fileIndex': 1
                }
            ],
            "teamUploadedFiles": None
        }

    def test_empty(self):
        data = {
            'workflow': {
                'has_submitted': True,
                'has_cancelled': False,
                'has_received_grade': True,
            },
            'team_info': {
                'team_name': 'Team1',
                'team_usernames': ['Bob', 'Alice'],
                'previous_team_name': None,
                'has_submitted': True,
            },
            'response': MockOraSubmissionAnswer([], []),
            'file_data': []
        }
        assert SubmissionSerializer(data).data == {
            'textResponses': [],
            'uploadedFiles': [],
            'teamUploadedFiles': None
        }


class TestDraftResponseSerializer(TestCase):

    def test_serializer(self):
        data = {
            'response': {
                'answer': {
                    'parts': [
                        {
                            'prompt': 'Prompt 1',
                            'text': 'Response to prompt 1'
                        },
                        {
                            'prompt': 'Prompt 2',
                            'text': 'Response to prompt 2'
                        },
                    ]
                }
            },
            'file_data': [
                FileDescriptor('www.mysite.com/files/1', 'desc-1', 'name-1', 1, True)._asdict(),
                FileDescriptor('www.mysite.com/files/22', 'desc-22', 'name-22', 22, True)._asdict(),
            ]
        }
        assert DraftResponseSerializer(data).data == {
            'textResponses': [
                'Response to prompt 1',
                'Response to prompt 2'
            ],
            'uploadedFiles': [
                {
                    'fileUrl': 'www.mysite.com/files/1',
                    'fileDescription': 'desc-1',
                    'fileName': 'name-1',
                    'fileSize': 1,
                    'fileIndex': 0
                },
                {
                    'fileUrl': 'www.mysite.com/files/22',
                    'fileDescription': 'desc-22',
                    'fileName': 'name-22',
                    'fileSize': 22,
                    'fileIndex': 1
                }
            ],
            'teamUploadedFiles': None,
        }

    def test_empty(self):
        data = {
            'response': {
                'answer': {
                    'parts': [
                        {
                            'prompt': 'Prompt 1',
                            'text': ''
                        },
                        {
                            'prompt': 'Prompt 2',
                            'text': ''
                        },
                    ]
                }
            },
            'file_data': []
        }
        assert DraftResponseSerializer(data).data == {
            'textResponses': ['', ''],
            'uploadedFiles': [],
            'teamUploadedFiles': None,
        }


@ddt.ddt
class TestPageDataResponseSerializer(TestCase):

    # Show full dictionary diffs
    maxDiff = None

    def test_integration_not_submitted(self):
        data = {
            'workflow': {
                'has_submitted': False,
                'has_cancelled': False,
                'has_received_grade': False,
            },
            'team_info': {
                'team_name': 'Team1',
                'team_usernames': ['Bob', 'Alice'],
                'previous_team_name': None,
                'has_submitted': False,
                'team_uploaded_files': [
                    TeamFileDescriptor('www.mysite.com/files/123', 'desc-123', 'name-123', 123, 'Bob')._asdict(),
                    TeamFileDescriptor('www.mysite.com/files/5555', 'desc-5555', 'name-5555', 5555, 'Billy')._asdict(),
                ]
            },
            'response': {
                'answer': {
                    'parts': [
                        {
                            'prompt': 'Prompt 1',
                            'text': 'Response to prompt 1'
                        },
                        {
                            'prompt': 'Prompt 2',
                            'text': 'Response to prompt 2'
                        },
                    ]
                }
            },
            'file_data': [
                FileDescriptor('www.mysite.com/files/1', 'desc-1', 'name-1', 1, True)._asdict(),
                FileDescriptor('www.mysite.com/files/22', 'desc-22', 'name-22', 22, True)._asdict(),
            ]
        }
        assert DraftResponseSerializer(data).data == {
            'textResponses': [
                'Response to prompt 1',
                'Response to prompt 2'
            ],
            'uploadedFiles': [
                {
                    'fileUrl': 'www.mysite.com/files/1',
                    'fileDescription': 'desc-1',
                    'fileName': 'name-1',
                    'fileSize': 1,
                    'fileIndex': 0
                },
                {
                    'fileUrl': 'www.mysite.com/files/22',
                    'fileDescription': 'desc-22',
                    'fileName': 'name-22',
                    'fileSize': 22,
                    'fileIndex': 1
                }
            ],
            'teamUploadedFiles': [
                {
                    'fileUrl': 'www.mysite.com/files/123',
                    'fileDescription': 'desc-123',
                    'fileName': 'name-123',
                    'fileSize': 123,
                    'uploadedBy': 'Bob'
                },
                {
                    'fileUrl': 'www.mysite.com/files/5555',
                    'fileDescription': 'desc-5555',
                    'fileName': 'name-5555',
                    'fileSize': 5555,
                    'uploadedBy': 'Billy'
                }
            ]
        }

    def test_integration_submitted(self):
        data = {
            'workflow': {
                'has_submitted': True,
                'has_cancelled': False,
                'has_received_grade': True,
            },
            'team_info': {
                'team_name': 'Team1',
                'team_usernames': ['Bob', 'Alice'],
                'previous_team_name': None,
                'has_submitted': True,
            },
            'response': MockOraSubmissionAnswer(
                [
                    'Response to prompt 1',
                    'Response to prompt 2'
                ],
                [
                    _mock_uploaded_file(1),
                    _mock_uploaded_file(22),
                    _mock_uploaded_file(123),
                    _mock_uploaded_file(5555),
                ]
            ),
            'file_data': []
        }
        assert SubmissionSerializer(data).data == {
            'textResponses': [
                'Response to prompt 1',
                'Response to prompt 2'
            ],
            'uploadedFiles': [
                {
                    'fileUrl': 'www.mysite.com/files/1',
                    'fileDescription': 'desc-1',
                    'fileName': 'name-1',
                    'fileSize': 1,
                    'fileIndex': 0
                },
                {
                    'fileUrl': 'www.mysite.com/files/22',
                    'fileDescription': 'desc-22',
                    'fileName': 'name-22',
                    'fileSize': 22,
                    'fileIndex': 1
                },
                {
                    'fileUrl': 'www.mysite.com/files/123',
                    'fileDescription': 'desc-123',
                    'fileName': 'name-123',
                    'fileSize': 123,
                    'fileIndex': 2
                },
                {
                    'fileUrl': 'www.mysite.com/files/5555',
                    'fileDescription': 'desc-5555',
                    'fileName': 'name-5555',
                    'fileSize': 5555,
                    'fileIndex': 3
                }
            ],
            "teamUploadedFiles": None,
        }
