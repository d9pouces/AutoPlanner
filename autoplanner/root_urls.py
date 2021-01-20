from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.static import serve
from djangofloor.scripts import load_celery
from djangofloor.views import robots

from autoplanner import views

__author__ = 'Matthieu Gallet'
load_celery()
admin.autodiscover()
admin_urls = admin.site.urls

urlpatterns = [url(r'^' + settings.MEDIA_URL[1:] + '(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
               url(r'^' + settings.STATIC_URL[1:] + '(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
               url(r'^robots\.txt$', robots),
               url(r'^org/(?P<organization_pk>\d+)\.html', views.organization, name='organization'),
               url(r'^org/start/(?P<organization_pk>\d+)\.html', views.schedule_task, name='schedule_start'),
               url(r'^org/cancel/(?P<organization_pk>\d+)\.html', views.cancel_schedule_task, name='cancel_schedule'),
               url(r'^org/ical/(?P<organization_pk>\d+)/all/(?P<title>.*)\.ics', views.generate_ics, name='ical'),
               url(r'^org/ical/(?P<organization_pk>\d+)/agent/(?P<agent_pk>\d+)/(?P<title>.*)\.ics',
                   views.generate_ics, name='ical'),
               url(r'^org/ical/(?P<organization_pk>\d+)/cat/(?P<category_pk>\d+)/(?P<title>.*)\.ics',
                   views.generate_ics, name='ical'),
               url(r'^tasks/apply_schedule_run/(?P<schedule_run_pk>\d+)\.html', views.apply_schedule_run,
                   name='apply_schedule_run'),
               url(r'^', include(admin_urls[:2])),
               url(r'^organization/(?P<organization_pk>\d+)/$', views.organization_index, name='organization_index'),
               url(r'^$', views.index, name='index'),
               ]

if settings.DEBUG and settings.USE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls)), ]
