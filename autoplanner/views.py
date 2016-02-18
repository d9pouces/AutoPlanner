# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from autoplanner.forms import MultiplyTaskForm
from autoplanner.models import Organization

__author__ = 'Matthieu Gallet'


def index(request):
    template_values = {
        'organizations': Organization.query(request).order_by('name')
    }
    return render_to_response('autoplanner/index.html', template_values, RequestContext(request))


def organization(request, organization_pk):
    org = get_object_or_404(Organization.query(request), pk=organization_pk)
    assert isinstance(org, Organization)
    tasks = org.task_set.all().order_by('start_time_slice')
    categories = org.category_set.all().order_by('name')
    template_values = {
        'organization': org,
        'tasks': tasks,
        'categories': categories,
    }
    return render_to_response('autoplanner/organization.html', template_values, RequestContext(request))


def multiply_task(request, task_pk):
    if request.method == 'POST':
        form = MultiplyTaskForm(request.POST)
    else:
        form = MultiplyTaskForm(initial={'source_task': task_pk})
    template_values = {'is_popup': 1, 'is_popup_var': 'is_popup',
                       }
    return render_to_response('autoplanner/multiply_task.html', template_values, RequestContext(request))