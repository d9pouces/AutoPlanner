# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url
from autoplanner import views

__author__ = 'Matthieu Gallet'


urls = [
    url('^org/(?P<organization_pk>\d+)\.html', views.organization, name='organization'),
    url('^index$', views.index, name='index'),
]
