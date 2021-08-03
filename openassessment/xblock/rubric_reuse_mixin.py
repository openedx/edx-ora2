""" Mixin for functionality around the reuse of rubrics between ORAs """
import logging

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import UsageKey
from xblock.core import XBlock

logger = logging.getLogger(__name__)


class RubricReuseMixin:

    def _get_course_ora_blocks(self):
        """
        Get all ORA blocks from the course.
        Both draft and published versions are queried, with preference to draft versions
        """
        if hasattr(self.runtime, 'modulestore'):
            return self.runtime.modulestore.get_items(
                self.location.course_key,
                qualifiers={'category': 'openassessment'},
            )
        else:
            logger.info(
                "_get_course_ora_blocks was called for %s but no modulestore was available",
                str(self.location)
            )
            return []

    def get_other_course_ora_blocks(self):
        """
        Returns a list of all ORA blocks in the course, excluding `self`, and any orphaned blocks.
        """
        blocks = self._get_course_ora_blocks()
        self_location = self.location.for_branch(None)

        def not_orphan_or_self(block):
            return block.parent is not None and block.location.for_branch(None) != self_location

        return [block for block in blocks if not_orphan_or_self(block)]

    def get_other_ora_blocks_for_rubric_editor_context(self):
        """
        Return a list of all other openassessment blocks in the course, in the format:
        {
            'display_name': <block display name>
            'location': <block location, as a string>
        }
        """
        other_blocks = self.get_other_course_ora_blocks()
        return [
            {
                'display_name': block.display_name,
                'location': str(block.location.for_branch(None))
            } for block in other_blocks
        ]

    @XBlock.json_handler
    def get_rubric(self, data, suffix=''):  # pylint: disable=unused-argument
        target_block_id = data.get('target_rubric_block_id')
        if target_block_id is None:
            return {'success': False, 'msg': self._('You must specify a block id from which to copy a rubric.')}
        try:
            target_ora_block_locator = UsageKey.from_string(target_block_id)
        except InvalidKeyError:
            return {'success': False, 'msg': self._('Invalid block id.')}
        try:
            rubric = self._get_rubric(target_ora_block_locator)
        except (TargetBlockNotORAException, TargetORABlockNotFoundException):
            return {
                'success': False,
                'msg': self._('No Open Response Assessment found in {course_id} with block id {block_id}').format(
                    course_id=self.location.course_key,
                    block_id=target_block_id
                )
            }
        return {
            'success': True,
            'rubric': {**rubric}
        }

    def _get_rubric(self, target_ora_block_locator):
        target_block = self._get_ora_block(target_ora_block_locator)
        if target_block.category != 'openassessment':
            logger.warning(
                "Requested rubric from %s which is %s not openassessment",
                target_ora_block_locator,
                target_block.category
            )
            raise TargetBlockNotORAException
        return {
            'criteria': target_block.rubric_criteria,
            'feedback_prompt': target_block.rubric_feedback_prompt,
            'feedback_default_text': target_block.rubric_feedback_default_text,
        }

    def _get_ora_block(self, target_ora_block_locator):
        if not hasattr(self.runtime, 'modulestore'):
            logger.warning(
                "Unable to lookup %s for rubric reuse because modulestore is not provided by the runtime",
                target_ora_block_locator
            )
            raise TargetORABlockNotFoundException

        try:
            return self.runtime.modulestore.get_item(target_ora_block_locator)
        except Exception as e:
            logger.warning("Unable to lookup %s for rubric reuse", target_ora_block_locator, exc_info=1)
            raise TargetORABlockNotFoundException from e


class TargetBlockNotORAException(Exception):
    """ Exception raised when _get_rubric is called with the location of a block that isn't an ORA """


class TargetORABlockNotFoundException(Exception):
    """ Exception raised when _get_rubric is called with the location of a block can't be found. """
