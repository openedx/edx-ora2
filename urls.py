from django.conf.urls import include, url
from django.contrib import admin
from django.views.i18n import JavaScriptCatalog

import openassessment.assessment.urls
import openassessment.fileupload.urls
import workbench.urls

# Packages to include in the JavaScript i18n strings
JS_INFO_DICT = {
    'packages': ('openassessment.xblock',),
}

urlpatterns = [
    # Django built-in
    url(r'^admin/', admin.site.urls),

    # Provided by XBlock
    url(r'^/?', include(workbench.urls)),

    # edx-ora2 apps
    url(r'^peer/evaluations/', include(openassessment.assessment.urls)),

    # JavaScript i18n
    url(r'^jsi18n/$', JavaScriptCatalog.as_view(), JS_INFO_DICT),

    # File upload to local filesystem
    url(r'^openassessment/storage', include(openassessment.fileupload.urls)),
]
