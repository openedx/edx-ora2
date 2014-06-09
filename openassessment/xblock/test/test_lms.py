"""
Tests for the LMS compatibility mixin for the OpenAssessment block.
"""
from ddt import ddt
from .base import scenario, XBlockHandlerTestCase


@ddt
class LmsMixinTest(XBlockHandlerTestCase):
    """Test the simple LMS-specific attributes used during grading."""

    @scenario('data/basic_scenario.xml')
    def test_simple_methods(self, xblock):
        self.assertTrue(xblock.has_score)
        self.assertFalse(xblock.has_dynamic_children())
        self.assertTrue(hasattr(xblock, 'weight'))

    @scenario('data/basic_scenario.xml')
    def test_max_score(self, xblock):
        self.assertEqual(xblock.max_score(), 20)
