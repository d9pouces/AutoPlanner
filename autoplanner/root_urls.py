# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url
from autoplanner import views

__author__ = 'Matthieu Gallet'


urls = [
    url('^org/(?P<organization_pk>\d+)\.html', views.organization, name='organization'),
    url('^tasks/multiply/(?P<task_pk>\d+)\.html', views.multiply_task, name='multiply_task'),
    url('^index$', views.index, name='index'),
]
