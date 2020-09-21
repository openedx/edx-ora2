"""
Test that we can export a block from the runtime (to XML) and re-import it without error.
"""

import copy
from io import BytesIO

from .base import XBlockHandlerTestCase, scenario
from .test_team import TEAMSET_ID


class TestExportImport(XBlockHandlerTestCase):

    @scenario('data/basic_scenario.xml')
    def test_export_import(self, xblock):

        # Store the fields of the XBlock
        old_fields = copy.deepcopy(xblock.fields)

        # Export the XBlock from the runtime
        output_buffer = BytesIO()
        self.runtime.export_to_xml(xblock, output_buffer)

        # Re-import the XBlock
        block_id = self.runtime.parse_xml_string(output_buffer.getvalue(), self.runtime.id_generator)
        new_block = self.runtime.get_block(block_id)

        # Check that the values of all fields are the same
        self.assertCountEqual(new_block.fields, old_fields)

    @scenario('data/team_submission.xml')
    def test_teams_export_import(self, xblock):
        # Ensure that we've loaded teams settings correctly from XML
        self.assertTrue(xblock.teams_enabled)
        self.assertEqual(TEAMSET_ID, xblock.selected_teamset_id)

        # Export the XBlock from the runtime
        output_buffer = BytesIO()
        self.runtime.export_to_xml(xblock, output_buffer)

        # Re-import the XBlock
        block_id = self.runtime.parse_xml_string(output_buffer.getvalue(), self.runtime.id_generator)
        new_block = self.runtime.get_block(block_id)

        # Check that we've loaded exported team settings correctly
        self.assertTrue(new_block.teams_enabled)
        self.assertEqual(TEAMSET_ID, new_block.selected_teamset_id)
