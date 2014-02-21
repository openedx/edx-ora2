from django.contrib import admin

from openassessment.peer.models import Assessment, AssessmentPart

admin.site.register(Assessment)
admin.site.register(AssessmentPart)
