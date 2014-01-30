from django.contrib import admin

from submissions.models import Score, StudentItem, Submission

admin.site.register(Score)
admin.site.register(StudentItem)
admin.site.register(Submission)
