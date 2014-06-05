"""
Test that we can export a block from the runtime (to XML) and re-import it without error.
"""

import copy
from StringIO import StringIO
from .base import XBlockHandlerTestCase, scenario


class TestExportImport(XBlockHandlerTestCase):

    @scenario('data/basic_scenario.xml')
    def test_export_import(self, xblock):

        # Store the fields of the XBlock
        old_fields = copy.deepcopy(xblock.fields)

        # Export the XBlock from the runtime
        output_buffer = StringIO()
        self.runtime.export_to_xml(xblock, output_buffer)

        # Re-import the XBlock
        block_id = self.runtime.parse_xml_string(output_buffer.getvalue(), self.runtime.id_generator)
        new_block = self.runtime.get_block(block_id)

        # Check that the values of all fields are the same
        self.assertItemsEqual(new_block.fields, old_fields)
