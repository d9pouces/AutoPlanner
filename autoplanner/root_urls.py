# -*- coding: utf-8 -*-

from django.views.i18n import javascript_catalog
from django.views.static import serve
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from djangofloor.views import robots
from djangofloor.scripts import load_celery

from autoplanner import views


__author__ = 'Matthieu Gallet'
load_celery()
admin.autodiscover()

urlpatterns = [url(r'^accounts/', include('allauth.urls')),
               url(r'^jsi18n/$', javascript_catalog, {'packages': ('djangofloor', 'django.contrib.admin', ), }),
               url(r'^' + settings.MEDIA_URL[1:] + '(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
               url(r'^' + settings.STATIC_URL[1:] + '(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
               url(r'^robots\.txt$', robots),
               url('^org/(?P<organization_pk>\d+)\.html', views.organization, name='organization'),
               url('^org/start/(?P<organization_pk>\d+)\.html', views.schedule_task, name='schedule_start'),
               url('^org/cancel/(?P<organization_pk>\d+)\.html', views.cancel_schedule_task, name='cancel_schedule'),
               url('^org/ical/(?P<organization_pk>\d+)\.ics', views.generate_ics, name='ical'),
               url('^org/ical/(?P<organization_pk>\d+)/agent/(?P<agent_pk>\d+)\.ics', views.generate_ics, name='ical'),
               url('^org/ical/(?P<organization_pk>\d+)/cat/(?P<category_pk>\d+)\.ics', views.generate_ics, name='ical'),
               url('^tasks/multiply/(?P<task_pk>\d+)\.html', views.multiply_task, name='multiply_task'),
               url(r'^chaining/', include('smart_selects.urls')),
               url(r'^', include(admin.site.urls)),
               ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls)), ]
