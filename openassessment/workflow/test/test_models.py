from django.test import TestCase
from mock import patch
from nose.tools import raises

from openassessment.workflow.models import emit_event
from openassessment.workflow.test.events import fake_event_logger

class TestEmitEvent(TestCase):

    def test_emit_wired_correctly(self):
        self.assertEqual(emit_event, fake_event_logger)
