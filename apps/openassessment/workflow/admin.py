from django.contrib import admin

from .models import AssessmentWorkflow

class AssessmentWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        'uuid', 'status', 'status_changed', 'submission_uuid', 'score'
    )

admin.site.register(AssessmentWorkflow, AssessmentWorkflowAdmin)
