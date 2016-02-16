# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from autoplanner.models import Organization

__author__ = 'Matthieu Gallet'


def index(request):
    template_values = {
        'organizations': Organization.query(request).order_by('name')
    }
    return render_to_response('autoplanner/index.html', template_values, RequestContext(request))


def organization(request, organization_pk):
    org = get_object_or_404(Organization.query(request), pk=organization_pk)
    events = org.event_set.all().order_by('start_time_slice')
    template_values = {
        'organization': org,
        'events': events,
    }
    return render_to_response('autoplanner/organization.html', template_values, RequestContext(request))