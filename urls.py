from django.conf import settings
from django.conf.urls import include, patterns, url
from django.contrib import admin

import openassessment.assessment.urls
import workbench.urls

admin.autodiscover()

# Packages to include in the JavaScript i18n strings
JS_INFO_DICT = {
    'packages': ('openassessment.xblock',),
}

urlpatterns = patterns(
    '',
    # Django built-in
    url(r'^admin/', include(admin.site.urls)),

    # Provided by XBlock
    url(r'^/?', include(workbench.urls)),

    # edx-ora2 apps
    url(r'^peer/evaluations/', include(openassessment.assessment.urls)),

    # JavaScript i18n
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', JS_INFO_DICT),
)

# We need to do explicit setup of the Django debug toolbar because autodiscovery
# causes problems when you mix debug toolbar >= 1.0 + django < 1.7, and the
# admin uses autodiscovery. See:
# http://django-debug-toolbar.readthedocs.org/en/1.0/installation.html#explicit-setup
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )
