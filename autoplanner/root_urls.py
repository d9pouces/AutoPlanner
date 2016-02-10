# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url

__author__ = 'Matthieu Gallet'


urls = [
    ('^index$', 'autoplanner.views.index'),
    
]

if __name__ == '__main__':
    import doctest
    doctest.testmod()