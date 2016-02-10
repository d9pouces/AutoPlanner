# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.template import RequestContext
__author__ = 'Matthieu Gallet'


def index(request):
    template_values = {}
    return render_to_response('autoplanner/index.html', template_values, RequestContext(request))

if __name__ == '__main__':
    import doctest
    doctest.testmod()