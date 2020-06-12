""" Admin file of workflow app """


from django.contrib import admin

from .models import AssessmentWorkflow, AssessmentWorkflowStep, TeamAssessmentWorkflow


class AssessmentWorkflowStepInline(admin.StackedInline):
    """Assessment Workflow Step"""
    model = AssessmentWorkflowStep
    extra = 0


class AssessmentWorkflowAdmin(admin.ModelAdmin):
    """Admin for the user's overall workflow through open assessment.

    Unlike many of the other models, we allow editing here. This is so that we
    can manually move a user's entry to "done" and give them a separate score
    in the submissions app if that's required. Unlike rubrics and assessments,
    there is no expectation of immutability for `AssessmentWorkflow`.
    """
    list_display = (
        'status', 'submission_uuid', 'course_id', 'item_id', 'status_changed'
    )
    list_filter = ('status',)
    search_fields = ('submission_uuid', 'course_id', 'item_id')
    inlines = (AssessmentWorkflowStepInline,)


class TeamAssessmentWorkflowAdmin(admin.ModelAdmin):
    """
    Admin for TeamAssessmentWorkflows.
    """

    list_display = (
        'id', 'status', 'team_submission_uuid', 'submission_uuid', 'course_id', 'item_id', 'status_changed'
    )
    list_filter = ('status',)
    search_fields = ('team_submission_uuid', 'submission_uuid', 'course_id', 'item_id')

    inlines = (AssessmentWorkflowStepInline,)


admin.site.register(AssessmentWorkflow, AssessmentWorkflowAdmin)
admin.site.register(TeamAssessmentWorkflow, TeamAssessmentWorkflowAdmin)
