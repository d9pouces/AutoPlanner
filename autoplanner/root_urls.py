# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url
from autoplanner import views

__author__ = 'Matthieu Gallet'


urls = [
    url('^org/(?P<organization_pk>\d+)\.html', views.organization, name='organization'),
    url('^org/start/(?P<organization_pk>\d+)\.html', views.schedule_task, name='schedule_start'),
    url('^org/cancel/(?P<organization_pk>\d+)\.html', views.cancel_schedule_task, name='cancel_schedule'),
    url('^tasks/multiply/(?P<task_pk>\d+)\.html', views.multiply_task, name='multiply_task'),
    url('^index$', views.index, name='index'),
]
