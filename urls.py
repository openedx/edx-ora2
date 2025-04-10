import workbench.urls

from django.contrib import admin
from django.urls import include, path
from django.urls import re_path
from django.views.i18n import JavaScriptCatalog

import openassessment.assessment.urls
import openassessment.fileupload.urls

# Packages to include in the JavaScript i18n strings
JS_INFO_DICT = {
    'packages': ('openassessment.xblock',),
}

urlpatterns = [
    # Django built-in
    re_path(r'^admin/', admin.site.urls),

    # Provided by XBlock
    re_path(r'^/?', include(workbench.urls)),

    # edx-ora2 apps
    path('peer/evaluations/', include(openassessment.assessment.urls)),

    # JavaScript i18n
    path('jsi18n/', JavaScriptCatalog.as_view(), JS_INFO_DICT),

    # File upload to local filesystem
    path('openassessment/storage',
            include(openassessment.fileupload.urls)),
]
