"""
Django admin models for openassessment
"""
import json

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils import html

from openassessment.assessment.models import (
    Assessment, AssessmentFeedback, PeerWorkflow, PeerWorkflowItem, Rubric,
    AIGradingWorkflow, AITrainingWorkflow, AIClassifierSet, AIClassifier
)
from openassessment.assessment.serializers import RubricSerializer


class RubricAdmin(admin.ModelAdmin):
    """
    Django admin model for Rubrics.
    """
    list_per_page = 20  # Loads of criteria summary are moderately expensive

    list_display = ('id', 'content_hash', 'criteria_summary')
    list_display_links = ('id', 'content_hash')
    search_fields = ('id', 'content_hash')
    readonly_fields = (
        'id', 'content_hash', 'structure_hash',
        'points_possible', 'criteria_summary', 'data'
    )

    def criteria_summary(self, rubric_obj):
        """Short description of criteria for presenting in a list."""
        rubric_data = RubricSerializer.serialized_from_cache(rubric_obj)
        return u", ".join(
            u"{} - {}: {}".format(criterion["name"], criterion['label'], criterion["points_possible"])
            for criterion in rubric_data["criteria"]
        )

    def data(self, rubric_obj):
        """Full JSON string of rubric, indented and HTML formatted."""
        rubric_data = RubricSerializer.serialized_from_cache(rubric_obj)
        return u"<pre>\n{}\n</pre>".format(
            html.escape(json.dumps(rubric_data, sort_keys=True, indent=4))
        )
    data.allow_tags = True


class PeerWorkflowItemInline(admin.StackedInline):
    """
    Django admin model for PeerWorkflowItems.
    """
    model = PeerWorkflowItem
    fk_name = 'author'
    raw_id_fields = ('author', 'scorer', 'assessment')
    extra = 0


class PeerWorkflowAdmin(admin.ModelAdmin):
    """
    Django admin model for PeerWorkflows.
    """
    list_display = (
        'id', 'student_id', 'item_id', 'course_id', 'submission_uuid',
        'created_at', 'completed_at', 'grading_completed_at',
    )
    search_fields = (
        'id', 'student_id', 'item_id', 'course_id', 'submission_uuid',
    )
    inlines = (PeerWorkflowItemInline,)


class AssessmentAdmin(admin.ModelAdmin):
    """
    Django admin model for Assessments.
    """
    list_display = (
        'id', 'submission_uuid', 'score_type', 'scorer_id', 'scored_at',
        'rubric_link',
    )
    search_fields = (
        'id', 'submission_uuid', 'score_type', 'scorer_id', 'scored_at',
        'rubric__content_hash',
    )
    readonly_fields = (
        'submission_uuid', 'rubric_link', 'scored_at', 'scorer_id',
        'score_type', 'points_earned', 'points_possible', 'feedback',
        'parts_summary',
    )
    exclude = ('rubric', 'submission_uuid')

    def rubric_link(self, assessment_obj):
        """
        Returns the rubric link for this assessment.
        """
        url = reverse(
            'admin:assessment_rubric_change',
            args=[assessment_obj.rubric.id]
        )
        return u'<a href="{}">{}</a>'.format(
            url, assessment_obj.rubric.content_hash
        )
    rubric_link.allow_tags = True
    rubric_link.admin_order_field = 'rubric__content_hash'
    rubric_link.short_description = 'Rubric'

    def parts_summary(self, assessment_obj):
        """
        Returns the parts summary of this assessment as HTML.
        """
        return "<br/>".join(
            html.escape(
                u"{}/{} - {} - {}: {} - {} - {}".format(
                    part.points_earned,
                    part.points_possible,
                    part.criterion.name,
                    part.criterion.label,
                    part.option.name if part.option else "None",
                    part.option.label if part.option else "None",
                    part.feedback,
                )
            )
            for part in assessment_obj.parts.all()
        )
    parts_summary.allow_tags = True


class AssessmentFeedbackAdmin(admin.ModelAdmin):
    """
    Django admin model for AssessmentFeedbacks.
    """
    list_display = ('id', 'submission_uuid',)
    search_fields = ('id', 'submission_uuid',)
    readonly_fields = (
        'submission_uuid', 'assessments_by', 'options', 'feedback_text'
    )
    exclude = ('assessments',)

    def assessments_by(self, assessment_feedback):
        """
        Gets all assessments for this feedback.
        """
        links = [
            u'<a href="{}">{}</a>'.format(
                reverse('admin:assessment_assessment_change', args=[asmt.id]),
                html.escape(asmt.scorer_id)
            )
            for asmt in assessment_feedback.assessments.all()
        ]
        return ", ".join(links)
    assessments_by.allow_tags = True


class AIGradingWorkflowAdmin(admin.ModelAdmin):
    """
    Django admin model for AIGradingWorkflows.
    """
    list_display = ('uuid', 'submission_uuid')
    search_fields = ('uuid', 'submission_uuid', 'student_id', 'item_id', 'course_id')
    readonly_fields = ('uuid', 'submission_uuid', 'student_id', 'item_id', 'course_id')


class AITrainingWorkflowAdmin(admin.ModelAdmin):
    """
    Django admin model for AITrainingWorkflows.
    """
    list_display = ('uuid',)
    search_fields = ('uuid', 'course_id', 'item_id',)
    readonly_fields = ('uuid', 'course_id', 'item_id',)


class AIClassifierInline(admin.TabularInline):
    """
    Django admin model for AIClassifiers.
    """
    model = AIClassifier


class AIClassifierSetAdmin(admin.ModelAdmin):
    """
    Django admin model for AICLassifierSets.
    """
    list_display = ('id',)
    search_fields = ('id',)
    inlines = [AIClassifierInline]


admin.site.register(Rubric, RubricAdmin)
admin.site.register(PeerWorkflow, PeerWorkflowAdmin)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(AssessmentFeedback, AssessmentFeedbackAdmin)
admin.site.register(AIGradingWorkflow, AIGradingWorkflowAdmin)
admin.site.register(AITrainingWorkflow, AITrainingWorkflowAdmin)
admin.site.register(AIClassifierSet, AIClassifierSetAdmin)
