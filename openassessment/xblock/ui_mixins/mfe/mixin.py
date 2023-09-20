"""
Data layer for ORA

XBlock handlers which surface info about an ORA, instead of being tied to views.
"""
from xblock.core import XBlock
from openassessment.xblock.ui_mixins.mfe.page_context_serializer import (
    PageDataSerializer,
)

from openassessment.xblock.ui_mixins.mfe.ora_config_serializer import (
    OraBlockInfoSerializer,
)


class MfeMixin:
    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):  # pylint: disable=unused-argument
        block_info = OraBlockInfoSerializer(self)
        return block_info.data

    @XBlock.json_handler
    def get_block_learner_submission_data(self, data, suffix=""):  # pylint: disable=unused-argument
        serializer_context = {"view": "submission"}
        page_context = PageDataSerializer(self, context=serializer_context)
        return page_context.data

    @XBlock.json_handler
    def get_block_learner_assessment_data(self, data, suffix=""):  # pylint: disable=unused-argument
        serializer_context = {"view": "assessment"}
        page_context = PageDataSerializer(self, context=serializer_context)
        return page_context.data
