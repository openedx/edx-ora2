"""
Django admin models for staffgrader
"""

from django.contrib import admin
from openassessment.staffgrader.models import SubmissionGradingLock


@admin.register(SubmissionGradingLock)
class SubmissionGradingLockAdmin(admin.ModelAdmin):
    """
    Django admin model for SubmissionGradingLock.
    """
    list_display = ('id', 'submission_uuid', 'owner_id', 'created_at', 'is_active')
    readonly_fields = ('is_active',)
    search_fields = ('submission_uuid',)

    # This allows us to have the nice boolean check/x icons in the list rather than "True"/"False"
    @admin.display(
        boolean=True
    )
    def is_active(self, lock):
        return lock.is_active
