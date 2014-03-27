from django.contrib import admin
from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response

from submissions import api as sub_api
from . import api as workflow_api
from .models import AssessmentWorkflow

class AssessmentWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        'uuid', 'status', 'status_changed', 'submission_uuid', 'score'
    )

admin.site.register(AssessmentWorkflow, AssessmentWorkflowAdmin)


class WorkflowAdminSite(admin.AdminSite):
    """
    Admin site for visualizing assessment workflows.
    Unlike other parts of the admin site, this is not tied to a particular model.
    """

    def get_urls(self):
        """
        Define URLs for the workflow admin site.
        """
        # We put our custom URLs before the Django admin URLs,
        # because we want ours to take priority (the default URLs tend to match permissively)
        return (
            patterns('',
                url(
                    r'courses',
                    self.admin_view(self.courses),
                    name='courses'
                ),
                url(
                    r'status/(?P<course_id>.+)/(?P<item_id>.+)$',
                    self.admin_view(self.status_counts),
                    name='status-counts'
                )
            ) + super(WorkflowAdminSite, self).get_urls()
        )

    def courses(self, request):
        """
        Show a list of courses and items with workflows.
        """
        courses_dict = sub_api.get_course_items()
        context = {
            "courses": [
                {
                    "course_id": course_id,
                    "items": [
                        {
                            "item_id": item_id,
                            "url": self._status_counts_url(course_id, item_id),
                        } for item_id in course_items
                    ]
                } for course_id, course_items in courses_dict.iteritems()
            ]
        }
        return render_to_response('workflow/admin/courses.html', context)

    def status_counts(self, request, course_id=None, item_id=None):
        """
        Display the status counts for workflows for a particular item in a course.
        """
        status_counts = workflow_api.get_status_counts(
            course_id=course_id, item_id=item_id, item_type="openassessment"
        )
        context = {
            "course_id": course_id,
            "item_id": item_id,
            "status_counts": status_counts,
            "num_submissions": sum(item['count'] for item in status_counts),
        }
        return render_to_response('workflow/admin/status_counts.html', context)

    def _status_counts_url(self, course_id, item_id):
        """
        Return a URL to the status counts page.

        Args:
            course_id (unicode): The ID of the course.
            item_id (unicode): The ID of the item in the course.

        Returns:
            unicode: URL to the status counts page.

        """
        kwargs = {'course_id': course_id, 'item_id': item_id}
        return reverse("admin:status-counts", kwargs=kwargs, current_app=self.name)


"""
To make the workflow admin URLs available, you need to add this to urls.py:

    from openassessment.workflow.admin import WORKFLOW_ADMIN_SITE
    url(r'^path/to/workflow/admin/', include(WORKFLOW_ADMIN_SITE.urls))

To reverse URLs to this site:

    from django.conf.urlresolvers import reverse
    reverse('admin:url-name', current_app='workflow-admin')

"""
WORKFLOW_ADMIN_SITE = WorkflowAdminSite('workflow-admin')
