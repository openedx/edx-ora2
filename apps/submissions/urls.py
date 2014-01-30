from django.conf.urls import patterns, url

urlpatterns = patterns(
    'submissions.views',
    url(
        r'^(?P<student_id>[^/]+)/(?P<course_id>[^/]+)/(?P<item_id>[^/]+)$',
        'get_submissions_for_student_item'
    ),
)
