from django.contrib import admin

from openassessment.peer.models import Assessment, AssessmentPart, Rubric, Criterion, CriterionOption

admin.site.register(Assessment)
admin.site.register(AssessmentPart)
admin.site.register(Rubric)
admin.site.register(Criterion)
admin.site.register(CriterionOption)

