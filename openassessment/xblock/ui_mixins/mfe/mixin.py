"""
Data layer for ORA

XBlock handlers which surface info about an ORA, instead of being tied to views.
"""
from xblock.core import XBlock

from openassessment.xblock.ui_mixins.mfe.serializers import OraBlockInfoSerializer


class MfeMixin:
    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):  # pylint: disable=unused-argument
        block_info = OraBlockInfoSerializer(self)
        return block_info.data
