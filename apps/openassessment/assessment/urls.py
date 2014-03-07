from django.conf.urls import patterns, url

urlpatterns = patterns(
    'openassessment.assessment.views',
    url(
        r'^(?P<student_id>[^/]+)/(?P<course_id>[^/]+)/(?P<item_id>[^/]+)$',
        'get_evaluations_for_student_item'
    ),
)
