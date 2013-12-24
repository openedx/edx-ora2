from django.conf.urls import patterns, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('peer_grading.views',
    url(r'^submit_peer_essay', 'submit_peer_essay'),
)
