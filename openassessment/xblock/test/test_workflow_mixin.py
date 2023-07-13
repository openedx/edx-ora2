"""
Tests for the workflow mixin.
"""

from unittest.mock import Mock
import ddt
from .base import XBlockHandlerTestCase, scenario


@ddt.ddt
class TestGetCourseWorkflowSettings(XBlockHandlerTestCase):
    """
    Tests for get_course_workflow_settings
    """

    @scenario('data/basic_scenario.xml')
    def test_no_course(self, xblock):
        """ If we can't load the course, we should be returning an empty dict """
        xblock.course = None
        assert xblock.get_course_workflow_settings() == {}

    @scenario("data/staff_grade_scenario.xml")
    def test_flex__no_peer_step(self, xblock):
        """ We don't include the flex override if there's no peer step """
        xblock.course = Mock(force_on_flexible_peer_openassessments=True)
        assert 'force_on_flexible_peer_openassessments' not in xblock.get_course_workflow_settings()

    @ddt.data(True, False)
    @scenario("data/peer_only_scenario.xml")
    def test_flex(self, xblock, course_setting):
        """ If there's a peer step, include the value of the course flex override """
        xblock.course = Mock(force_on_flexible_peer_openassessments=course_setting)
        settings = xblock.get_course_workflow_settings()
        assert settings['force_on_flexible_peer_openassessments'] == course_setting
