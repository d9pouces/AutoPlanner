# -*- coding: utf-8 -*-
import datetime
import re

from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR, get_content_type_for_model
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib import messages
from django.contrib.admin.utils import quote
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from autoplanner.admin import OrganizationAdmin
from autoplanner.forms import MultiplyTaskForm
from autoplanner.models import Organization, Task


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
    obj = get_object_or_404(Task, pk=task_pk)
    # noinspection PyProtectedMember
    model_admin = admin.site._registry[Organization]
    assert isinstance(model_admin, OrganizationAdmin)
    # noinspection PyProtectedMember
    opts = model_admin.model._meta
    if request.method == 'POST':
        form = MultiplyTaskForm(request.POST)
        if form.is_valid():
            until_src = form.cleaned_data['until']
            every_src = form.cleaned_data['every']
            assert isinstance(until_src, datetime.datetime)
            limit = datetime.datetime(year=until_src.year, month=until_src.month, day=until_src.day,
                                      hour=23, minute=59, second=59, tzinfo=obj.start_time_slice.tzinfo)
            to_create = []
            increment = datetime.timedelta(days=every_src)
            start_time_slice = obj.start_time_slice + increment
            end_time_slice = obj.end_time_slice + increment
            matcher = re.match(r'^(.*)\s+\((\d+)\)', obj.name)
            if matcher:
                new_name = matcher.group(1)
                name_index = int(matcher.group(2)) + 1
            else:
                new_name = obj.name
                name_index = 2
            while start_time_slice < limit:
                new_task = Task(organization_id=obj.organization_id, category_id=obj.category_id,
                                name='%s (%d)' % (new_name, name_index),
                                start_time_slice=start_time_slice, end_time_slice=end_time_slice)
                to_create.append(new_task)
                start_time_slice += increment
                end_time_slice += increment
                name_index += 1
            if to_create:
                Task.objects.bulk_create(to_create)
            if len(to_create) > 1:
                messages.info(request, _('%(count)d tasks have been created.') % {'count': len(to_create)})
            elif to_create:
                messages.info(request, _('A task has been created.'))
            new_url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                    args=(quote(task_pk), ), current_app=model_admin.admin_site.name)
            return HttpResponseRedirect(new_url)
    else:
        form = MultiplyTaskForm(initial={'source_task': obj})
    template_values = {'is_popup': 0, }

    app_label = opts.app_label
    preserved_filters = model_admin.get_preserved_filters(request)
    form_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, '?')
    view_on_site_url = model_admin.get_view_on_site_url(obj)
    template_values.update({
        'add': False,
        'change': True,
        'form': form,
        'obj': obj,
        'has_change_permission': model_admin.has_change_permission(request, obj),
        'has_delete_permission': False,
        'has_add_permission': False,
        'has_file_field': False,
        'has_absolute_url': view_on_site_url is not None,
        'absolute_url': view_on_site_url,
        'form_url': form_url,
        'opts': opts,
        'content_type_id': get_content_type_for_model(Task).pk,
        'save_as': True,
        'save_on_top': False,
        'media': model_admin.media,
        'to_field_var': TO_FIELD_VAR,
        'is_popup_var': IS_POPUP_VAR,
        'app_label': app_label,
        'show_save': False,
    })

    return render_to_response('autoplanner/multiply_task.html', template_values, RequestContext(request))