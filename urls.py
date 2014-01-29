from django.conf.urls import include, patterns, url
from django.contrib import admin

import submissions.urls

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^submissions', include(submissions.urls)),
    url(r'^admin/', include(admin.site.urls)),
)