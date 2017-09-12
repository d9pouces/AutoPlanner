from django.conf.urls import url

from autoplanner import views

__author__ = 'Matthieu Gallet'
app_name = 'autoplanner'
urlpatterns = [
    url(r'^organization/(?P<organization_pk>\d+)/$', views.organization_index, name='organization_index'),

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
]
