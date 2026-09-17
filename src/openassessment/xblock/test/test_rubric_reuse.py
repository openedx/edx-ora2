""" Unit tests for rubric_reuse_mixin.py """
from contextlib import contextmanager
from unittest import mock
import json

from opaque_keys.edx.keys import UsageKey

from openassessment.xblock.test.base import XBlockHandlerTestCase
from openassessment.xblock.rubric_reuse_mixin import (
    RubricReuseMixin, TargetBlockNotORAException, TargetORABlockNotFoundException
)


class MockBlock(RubricReuseMixin):
    """ A mock Xblock for testing the RubricReuseMixin """
    def __init__(self):
        self.runtime = None
        self.location = mock.Mock()
        self.category = 'openassessment'
        self.parent = mock.Mock()
        self._ = lambda x: x

    def save(self):
        pass


class RubricReuseMixinUnitTests(XBlockHandlerTestCase):
    """ Unit tests for RubricReuseMixin """

    BLOCK_LOCATION = "block-v1:edx+Rubrics101+T1+type@openassessment+block@fb668396b505470e914bad8b3178e9e7"
    OTHER_BLOCK_LOCATION = "block-v1:edx+Rubrics101+T1+type@openassessment+block@90b4edff50bc47d9ba037a3180c44e97"
    OTHER_COURSE_BLOCK_LOCATION = (
        "block-v1:edx+Astronomy201+T4+type@openassessment+block@9d1af6220a4d4ecbafb22a3506effcce"
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.block_location = UsageKey.from_string(cls.BLOCK_LOCATION)
        cls.other_block_location = UsageKey.from_string(cls.OTHER_BLOCK_LOCATION)
        cls.other_course_block_location = UsageKey.from_string(cls.OTHER_COURSE_BLOCK_LOCATION)

    def setUp(self):
        super().setUp()
        self.block = MockBlock()
        self.block.location = self.block_location

    def _make_mock_ora_block(self, orphan=False, location=None):
        """ Helper function to create a mock ORA XBlock """
        mock_block = mock.Mock(category='openassessment')
        if orphan:
            mock_block.parent = None
        if location is not None:
            mock_block.location = location
        return mock_block

    def mock_get_course_ora_blocks(self, **kwargs):
        """ Helper funtion to mock RubricReuseMixin._get_course_ora_blocks """
        # pylint: disable=protected-access
        self.block._get_course_ora_blocks = mock.MagicMock(**kwargs)

    @contextmanager
    def mock_get_ora_block(self, **kwargs):
        """ Context manager for mocking out RubricReuseMixin._get_ora_block """
        with mock.patch.object(RubricReuseMixin, '_get_ora_block', mock.MagicMock(**kwargs)):
            yield

    # ----------------------------------
    # get_other_course_ora_blocks
    # ----------------------------------

    def test_get_other_course_ora_blocks(self):
        """ Test that the current block will not be included from get_other_course_ora_blocks """
        other_ora_blocks = [self._make_mock_ora_block() for _ in range(5)]
        course_ora_blocks = [self.block] + other_ora_blocks
        self.mock_get_course_ora_blocks(return_value=course_ora_blocks)
        result = self.block.get_other_course_ora_blocks()

        self.assertEqual(set(result), set(other_ora_blocks))

    def test_get_other_course_ora_blocks__none(self):
        """ Test for get_other_course_ora_blocks when there are no other ORAs in the course """
        self.mock_get_course_ora_blocks(return_value=[self.block])
        self.assertEqual(self.block.get_other_course_ora_blocks(), [])

    def test_get_other_course_ora_blocks__filter_orphan(self):
        """ Test that get_other_course_ora_blocks does not include orphaned ORA blocks """
        non_orphans = [
            self._make_mock_ora_block() for _ in range(3)
        ]
        orphans = [
            self._make_mock_ora_block(orphan=True) for _ in range(2)
        ]

        course_ora_blocks = [self.block] + non_orphans + orphans
        self.mock_get_course_ora_blocks(return_value=course_ora_blocks)

        result = self.block.get_other_course_ora_blocks()
        self.assertEqual(set(result), set(non_orphans))

    # -----------------------------------------------
    # get_other_ora_blocks_for_rubric_editor_context
    # -----------------------------------------------

    def get_other_ora_blocks_for_rubric_editor_context(self):
        other_blocks = [self._make_mock_ora_block() for _ in range(5)]
        with mock.patch.object(self.block, 'get_other_course_ora_blocks') as mock_get_other_blocks:
            mock_get_other_blocks.return_value = other_blocks
            context = self.block.get_other_ora_blocks_for_rubric_editor_context()
        expected_context = [{'display_name': block.display_name, 'location': block.location} for block in other_blocks]
        self.assertEqual(
            set(expected_context),
            set(context),
        )

    # -----------
    # get_rubric
    # -----------

    def _request_get_rubric(self, payload):
        """ Helper function for calling the XBlock JSON handler """
        return self.request(
            self.block,
            'get_rubric',
            json.dumps(payload),
            response_format='json'
        )

    def test_get_rubric(self):
        """ Test that get_rubric will get a rubric correctly"""
        another_ora = self._make_mock_ora_block(location=self.other_block_location)
        # Mocks aren't json serializable so we have to give these values here
        another_ora.rubric_criteria = "this is an arbitrary value for the rubric"
        another_ora.rubric_feedback_prompt = "this is an arbitrary value for the feedback prompt"
        another_ora.rubric_feedback_default_text = "this is an arbitrary value for the default feedback text"

        with self.mock_get_ora_block(return_value=another_ora):
            resp = self._request_get_rubric({'target_rubric_block_id': str(self.other_block_location)})
        self.assertTrue(resp['success'])
        self.assertEqual(resp['rubric']['criteria'], another_ora.rubric_criteria)
        self.assertEqual(resp['rubric']['feedback_prompt'], another_ora.rubric_feedback_prompt)
        self.assertEqual(resp['rubric']['feedback_default_text'], another_ora.rubric_feedback_default_text)

    def test_get_rubric__missing_param(self):
        """ Test for get_rubric error behavior when called with missing params """
        resp = self._request_get_rubric({})
        self.assertFalse(resp['success'])
        self.assertEqual(resp['msg'], 'You must specify a block id from which to copy a rubric.')

    def test_get_rubric__invalid_key(self):
        """ Test for get_rubric error behavior when the parameter is an invalid key """
        resp = self._request_get_rubric({'target_rubric_block_id': 'invalidKEEEEY'})
        self.assertFalse(resp['success'])
        self.assertEqual(resp['msg'], 'Invalid block id.')

    def test_get_rubric__not_found(self):
        """ Test for get_rubric error behavior when the requested block can't be found """
        with self.mock_get_ora_block(side_effect=TargetORABlockNotFoundException):
            resp = self._request_get_rubric({'target_rubric_block_id': self.OTHER_BLOCK_LOCATION})
        self.assertFalse(resp['success'])
        self.assertRegex(
            resp['msg'],
            r'No Open Response Assessment found in (.*?) with block id',
        )

    def test_get_rubric__not_ora(self):
        """ Test for get_rubric error behavior when the requested block isn't an ORA block """
        with self.mock_get_ora_block(side_effect=TargetBlockNotORAException):
            resp = self._request_get_rubric({'target_rubric_block_id': self.OTHER_BLOCK_LOCATION})
        self.assertFalse(resp['success'])
        self.assertRegex(
            resp['msg'],
            r'No Open Response Assessment found in (.*?) with block id',
        )

    # ----------------------------------------
    # tests for mocked modulestore functions
    # ----------------------------------------

    def _mock_runtime_modulestore_get_items(self, **kwargs):
        """ Mock the xblock's runtime and runtime.modulestore.get_item method """
        self.block.runtime = mock.Mock()
        self.block.runtime.modulestore.get_items = mock.Mock(**kwargs)

    def _mock_runtime_modulestore_get_item(self, **kwargs):
        """ Mock the xblock's runtime and runtime.modulestore.get_items method """
        self.block.runtime = mock.Mock()
        self.block.runtime.modulestore.get_item = mock.Mock(**kwargs)

    def _mock_runtime_no_modulestore(self):
        """ Mock the xblock to have a runtime with no modulestore (or any other attributes) """
        self.block.runtime = mock.Mock(spec=[])

    def test__get_course_ora_blocks(self):
        """ test for normal behavior of _get_course_ora_blocks """
        self._mock_runtime_modulestore_get_items()
        result = self.block._get_course_ora_blocks()  # pylint: disable=protected-access
        self.block.runtime.modulestore.get_items.assert_called_once_with(
            self.block.location.course_key,
            qualifiers={'category': 'openassessment'},
        )
        self.assertEqual(result, self.block.runtime.modulestore.get_items.return_value)

    def test__get_course_ora_blocks__no_modulestore(self):
        """ test for behavior of _get_course_ora_blocks when the runtime does not provide a modulestore"""
        self._mock_runtime_no_modulestore()
        self.assertEqual(self.block._get_course_ora_blocks(), [])  # pylint: disable=protected-access

    def test__get_ora_block(self):
        """ test for normal behavior of _get_ora_block """
        self._mock_runtime_modulestore_get_item()
        result = self.block._get_ora_block(self.block_location)  # pylint: disable=protected-access
        self.block.runtime.modulestore.get_item.assert_called_once()
        self.block.runtime.modulestore.get_item.assert_called_once_with(self.block_location)
        self.assertEqual(self.block.runtime.modulestore.get_item.return_value, result)

    def test___get_ora_block__exception(self):
        """ test for error behavior when an exception is raised by the modulestore """
        self._mock_runtime_modulestore_get_item(side_effect=Exception)
        with self.assertRaises(TargetORABlockNotFoundException):
            self.block._get_ora_block(self.block_location)  # pylint: disable=protected-access

    def test__get_ora_block__no_modulestore(self):
        """ test for error behavior of _get_ora_block when the runtime does not provide a modulestore"""
        self._mock_runtime_no_modulestore()
        with self.assertRaises(TargetORABlockNotFoundException):
            self.block._get_ora_block(self.block_location)  # pylint: disable=protected-access
