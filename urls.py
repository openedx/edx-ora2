from django.conf.urls import include, patterns, url
from django.contrib import admin

import submissions.urls
import workbench.urls

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Django built-in
    url(r'^admin/', include(admin.site.urls)),

    # Provided by XBlock
    url(r'^workbench/', include(workbench.urls))

    # edx-tim apps
#    url(r'^submissions', include(submissions.urls)),
)