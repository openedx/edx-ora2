from django.contrib import admin

from submissions.models import Score, StudentItem, Submission

class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'student_item', 'uuid', 'attempt_number', 'submitted_at', 'created_at',
        'raw_answer', 'scores'
    )

    def scores(self, obj):
        return ", ".join(
            "{}/{}".format(score.points_earned, score.points_possible)
            for score in Score.objects.filter(submission=obj.id)
        )

admin.site.register(Score)
admin.site.register(StudentItem)
admin.site.register(Submission, SubmissionAdmin)
