from django.conf.urls import url, patterns

urlpatterns = patterns(
    'submissions.views',
    url(r'^submissions/(?P<student_id>[^/]+)/(?P<course_id>[^/]+)/(?P<item_id>[^/]+)$',
        'get_submissions_for_student_item'),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
)


