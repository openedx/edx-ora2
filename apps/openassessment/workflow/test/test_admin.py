# -*- coding: utf-8 -*-
"""
Tests for the workflow admin site.
"""

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from submissions import api as sub_api
import openassessment.workflow.api as workflow_api


class WorkflowAdminSiteTest(TestCase):
    """
    View-level tests of the workflow admin site.
    """

    STUDENT_ITEM = {
        "student_id": "Omar Little",
        "course_id": "test/1/1",
        "item_id": "peer-assessment",
        "item_type": "openassessment",
    }

    ANSWER = u"ﾑ ﾶﾑ刀 ﾶu丂ｲ んﾑ√乇 ﾑ cod乇."

    def setUp(self):
        """
        Create submissions and workflows.
        """
        super(WorkflowAdminSiteTest, self).setUp()

        # Log in as an admin user
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        self.client.login(username='admin', password='admin')

        # Create a submission and workflow
        submission = sub_api.create_submission(self.STUDENT_ITEM, self.ANSWER)
        workflow_api.create_workflow(submission['uuid'])

    def test_courses_page(self):
        url = reverse('admin:courses', current_app='workflow-admin')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.template.name, 'workflow/admin/courses.html')

        expected_courses = [{
            'course_id': u'test/1/1',
            'items': [{
                'item_id': u'peer-assessment',
                'url': '/workflow/admin/status/test/1/1/peer-assessment'
            }]
        }]
        self.assertEqual(resp.context['courses'], expected_courses)

    def test_status_counts_page(self):
        kwargs = {
            'course_id': self.STUDENT_ITEM['course_id'],
            'item_id': self.STUDENT_ITEM['item_id'],
        }
        url = reverse('admin:status-counts', kwargs=kwargs, current_app='workflow-admin')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.template.name, 'workflow/admin/status_counts.html')
        self.assertEqual(resp.context['course_id'], self.STUDENT_ITEM['course_id'])
        self.assertEqual(resp.context['item_id'], self.STUDENT_ITEM['item_id'])
        self.assertEqual(resp.context['num_submissions'], 1)
        self.assertItemsEqual(
            resp.context['status_counts'],
            [
                {'status': 'peer', 'count': 1},
                {'status': 'self', 'count': 0},
                {'status': 'waiting', 'count': 0},
                {'status': 'done', 'count': 0}
            ]
        )
